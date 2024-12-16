# 이미지 크롤링 프로그램

사용자가 입력한 키워드를 기반으로 네이버 이미지 검색 결과에서 이미지를 자동으로 스크랩하는 파이썬 스크립트  
스크립트는 이미지를 로컬에 저장하고, 해당 이미지의 원본 URL과 이미지 URL을 엑셀 파일에 기록

## 설치 방법
1. Python 3.9 설치  
공식 웹사이트에서 Python 3.9을 다운로드하고 설치


2. 레포지토리 클론
git clone https://github.com/ilestri/crawling.git


3. 필요한 라이브러리 설치  
   pip install selenium  
   pip install webdriver-manager  
   pip install openpyxl  
   pip install requests  

ㅁㄴㅇㄹ
4. 특징  
   자동 이미지 스크레이핑: 사용자가 입력한 키워드를 기반으로 네이버에서 이미지를 수집합니다.  
   중복 처리: 원본 URL을 확인하여 중복 이미지를 다운로드하지 않습니다.  
   데이터 기록: 이미지 이름, 원본 URL, 이미지 URL을 엑셀 파일에 저장합니다.  
   에러 처리: 스크레이핑 및 다운로드 중 발생하는 문제를 관리하는 견고한 에러 처리 기능.  
   설정 가능: 다운로드할 이미지의 최대 수를 설정할 수 있습니다.

## 사용방법
1. 프롬프트 실행
2. 프롬프트에 스크랩 할 검색어 입력
3. crawling 루트 폴더에 이미지 폴더와 엑셀이 생김