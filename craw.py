#!/usr/local/bin/python3
import sys
import sqlite3
import datetime
import requests
import os
import errno
import configparser
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select

config = configparser.ConfigParser()
config.read('config.ini')

USER_ID = config['DEFAULT']['USER_ID']
PASSWORD = config['DEFAULT']['PASSWORD']
CHROME_DRIVER_PATH = "./chromedriver"
BILL_DB = "./bill.db"
OUTPUT_HTML = "./result.html"

LOGIN_URI = 'https://www.open.go.kr/pa/member/openLogin/memberLogin.do'
BILLING_LIST_URI = 'https://www.open.go.kr/pa/billing/openBilling/openBillingList.do'

# driver setting
driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH)

from_date = None
if(len(sys.argv) > 1) :
	from_date= sys.argv[1]

def wait_until(sec, until):
	WebDriverWait(driver, sec).until(until)

def login():
	# login
	driver.get(LOGIN_URI)

	memberId = driver.find_element_by_name("mberId")
	memberId.clear()
	memberId.send_keys(USER_ID)

	pwd = driver.find_element_by_name("pwd")
	pwd.clear()
	pwd.send_keys(PASSWORD)

	button = driver.find_element_by_id("loginSubmitBtn")
	button.click()

	wait_until(30, EC.presence_of_element_located((By.ID, 'loginCheckTime')))

def init_page_list():
	# list
	driver.get(BILLING_LIST_URI)
	wait_until(10, EC.invisibility_of_element_located((By.ID, 'imgLoading')))

	# select = Select(driver.find_element_by_id('prcsStsCdSch'))
	# select.select_by_visible_text('처리완료')

	# select = driver.find_element_by_id('rowPage')
	# driver.execute_script('arguments[0].getElementsByTagName("option")[3].value = 10000', select)

	if from_date :
		driver.execute_script('document.getElementById("stRceptPot").value = "'+from_date+'"')

	select = Select(driver.find_element_by_id('rowPage'))
	select.select_by_visible_text('100')

	button = driver.find_element_by_id("searchBtn")
	button.click()
	wait_until(10, EC.invisibility_of_element_located((By.ID, 'imgLoading')))

	if len(driver.find_element_by_class_name("pagination").text) > 1 :
		lastPageLink = driver.find_elements_by_class_name("direction")[3]
		lastPageLink.click()

	wait_until(10, EC.invisibility_of_element_located((By.ID, 'imgLoading')))

def next_page():
	prevLink = driver.find_elements_by_class_name("direction")[1]
	print("prevLink : ")
	print(prevLink.text)
	prevLink.click()
	wait_until(10, EC.invisibility_of_element_located((By.ID, 'imgLoading')))

def get_rows():
	if not driver.current_url.startswith(BILLING_LIST_URI) :
		init_page_list()
	table_id = driver.find_element(By.ID, 'openBillingTable')
	rows = table_id.find_elements(By.TAG_NAME, "tbody")[0].find_elements(By.TAG_NAME, "tr")
	return rows

def set_row(idx):
	row = get_rows()[idx]
	cols = row.find_elements(By.TAG_NAME, "td")
	if len(cols) == 1 :
		print("empty!")
		driver.close()
		exit()

	bill = dict( id = cols[1].text, 
		regist_date = cols[2].text,
		subject = cols[3].text,
		city = cols[4].text,
		status = cols[5].text,
		proc_date = cols[6].text,
		etc = cols[7].text,
		contents = '',
		file_name = '',
		update_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
		)
	if find_finished(bill['id']) :
		return

	if bill['status'].startswith(u"처리완료") :
		cols[3].find_element(By.TAG_NAME, "a").click()
		wait_until(10, EC.invisibility_of_element_located((By.ID, 'imgLoading')))

		bill['contents'] = driver.find_element_by_id('oppCn').text.replace("\\n","")
		file_area = driver.find_element_by_id('dntcFileListTxt')

		if len(file_area.text) > 1 :
			href = file_area.find_element(By.TAG_NAME, "a").get_attribute("href");
			if file_area.find_element(By.TAG_NAME, "a").text == u"본인인증" :
				bill['etc'] = u'본인인증'
				driver.execute_script('document.getElementById("modal_back").remove()')
				
			else :
				file_name = driver.find_element_by_id('dntcFileListTxt').find_element(By.TAG_NAME, "a").text

				s = requests.Session()
				for cookie in driver.get_cookies(): 
					c = {cookie['name']: cookie['value']} 
					s.cookies.update(c)
				res = s.get(href)

				# file write
				file_path = './'+bill['subject']+'/'+bill['city']+'/'+file_name
				if not os.path.exists(os.path.dirname(file_path)):
					try:
						os.makedirs(os.path.dirname(file_path))
					except OSError as exc: # Guard against race condition
						if exc.errno != errno.EEXIST:
							raise
				with open(file_path, "wb") as f:
					f.write(res.content)

				bill['file_name'] = file_name

		upsert(bill)

		button = driver.find_element_by_id("listBnt2")
		button.click()
		
		wait_until(10, EC.invisibility_of_element_located((By.ID, 'imgLoading')))
	else :
		upsert(bill)
	

def create_table():
	with sqlite3.connect(BILL_DB) as conn:
		cur = conn.cursor()
		cur.execute("CREATE TABLE IF NOT EXISTS bills (id INTEGER PRIMARY KEY ON CONFLICT REPLACE, regist_date TEXT, subject TEXT, city TEXT, status TEXT, proc_date TEXT, etc TEXT, contents TEXT, file_name TEXT, update_date TEXT);")

def find_finished(id):
	with sqlite3.connect(BILL_DB) as conn:
		cur = conn.cursor()
		for row in cur.execute("SELECT * FROM bills WHERE id = ? and  status LIKE '처리완료%'", (id, )) :
			return row[0]
		else : 
			return None

def upsert(bill):
	with sqlite3.connect(BILL_DB) as conn:
		cur = conn.cursor()
		cur.execute("INSERT OR REPLACE INTO bills (id, regist_date, subject, city, status, proc_date, etc, contents, file_name, update_date) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (bill['id'], bill['regist_date'], bill['subject'], bill['city'], bill['status'], bill['proc_date'], bill['etc'], bill['contents'], bill['file_name'], bill['update_date']))

def write_header():
	with open(OUTPUT_CSV, "w", encoding="utf-8") as f:
		f.write("접수번호, 접수일, 제목, 처리기관명, 처리상태, 처리일자, 비고, 공개내용, 파일이름"+"\n")

def write_bill(bill):
	with open(OUTPUT_CSV, "a", encoding="utf-8") as f:
		f.write(",".join(bill.values()).replace("\n","")+"\n")

create_table()
login()
init_page_list()

while True:
	rows = get_rows()
	row_size = len(rows)
	# write_header()
	for idx in reversed(range(row_size)) :
		set_row(idx)
	print(driver.find_elements_by_class_name("pagination")[0].find_element(By.TAG_NAME, "strong").text)
	if driver.find_elements_by_class_name("pagination")[0].find_element(By.TAG_NAME, "strong").text == "1":
		break
	next_page()

driver.close()

with open(OUTPUT_HTML, "w") as f:
	html = ""
	html += '<link rel="stylesheet" href="https://unpkg.com/purecss@1.0.0/build/pure-min.css" integrity="sha384-nn4HPE8lTHyVtfCBi5yW9d20FjT8BJwUXyWZT9InLYax14RDjBj46LmSztkmNP9w" crossorigin="anonymous">'
	html += '<table class="pure-table pure-table-horizontal">'
	html += "<thead>"
	html += "<tr>"
	html += "<th>접수번호</th><th>접수일</th><th>제목</th><th>처리기관명</th><th>처리상태</th><th>처리일자</th><th>비고</th><th>공개내용</th><th>파일이름</th><th>수정일</th>"
	html += "</tr>"
	html += "</thead>"
	html += "<tbody>"
	with sqlite3.connect(BILL_DB) as conn:
		cur = conn.cursor()
		for row in cur.execute("SELECT * FROM bills order by id desc") :
			html += "<tr>"
			for m in range(0,10):
				html += "<td>"
				if m == 8 :
					html+= '<a href="file:///'+os.getcwd()+'/'+str(row[2])+'/'+str(row[3])+'/'+str(row[m])+'">'+str(row[m])+'</a>'
				else :
					html+= str(row[m])
				html += "</td>"
			html += "</tr>"
	html += "</tbody>"
	f.write(html)

print("finish!")
exit()





