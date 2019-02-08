import sqlite3, os

BILL_DB = "./bill.db"
OUTPUT_HTML = "./result.html"

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

