# open.go.kr
selenium을 이용한 open.go.kr 크롤링 

## 실행 방법

1. [python3 설치](https://www.python.org/downloads/)
2. pip install requests
3. pip install selenium
4. [프로젝트 다운로드](https://github.com/serendip811/open.go.kr/archive/master.zip)
5. [크롬 드라이버 설치](http://chromedriver.chromium.org/downloads)
6. config.ini 수정
	- user_id : 로그인 사용자 아이디
	- password : 로그인 사용자 패스워드
	- from_date : 검색 시작 날짜
7. > python craw.py

## 실행 가능한 파일로 만들기

1. [pyinstaller 설치](https://www.pyinstaller.org)
2. > pyinstaller --onefile craw.py

## 동작
1. selenium webdriver가 open.go.kr에 로그인 후 목록 조회
2. sqlite db에 upsert (bill.db)
3. 조회 완료 시 db 읽어서 html파일로 결과 출력 (result.html)
