# 필요한 라이브러리 불러오기
from selenium import webdriver
from selenium.webdriver.common.by import By
import os
import openpyxl
import time
from datetime import datetime
import requests
import base64
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions

# 크롬 드라이버 최신 버전 설정 (현재 오류 발생)
# service = ChromeService(executable_path=ChromeDriverManager().install())

# 크롬 드라이버 설정(오류 개선)
chrome_install = ChromeDriverManager().install()

folder = os.path.dirname(chrome_install)
chromedriver_path = os.path.join(folder, "chromedriver.exe")

service = ChromeService(chromedriver_path)

# Chrome Driver 옵션 설정
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')

# 웹드라이버 설정 및 페이지 접근
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10)  # 10초 대기


# 폴더 생성 함수
def createFolder(name):
  if not os.path.exists(f'./{name}'):
    os.makedirs(f'./{name}')
    print(f'{name} 폴더 생성 완료')
  else:
    print('이미 존재하는 폴더입니다.')


# 인코딩 문제 해결을 위한 함수
def save_base64_image(data, file_path):
  """Base64로 인코딩된 이미지 데이터를 파일로 저장합니다."""
  image_data = base64.b64decode(data)
  with open(file_path, 'wb') as f:
    f.write(image_data)


# 검색어 입력
input_name = input('검색어 입력: ').strip().replace('/', '_').replace('\\', '_')
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
folder_name = f"{input_name}_{current_time}"

# 페이지 접근
driver.get(
    f'https://search.naver.com/search.naver?where=image&sm=tab_jum&query={input_name}')
wait.until(EC.presence_of_all_elements_located(
    (By.CSS_SELECTOR, '._fe_image_tab_content_thumbnail_image')))

# 스크롤 다운
scroll_pause_time = 3
last_height = driver.execute_script("return document.body.scrollHeight")

while True:
  driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
  time.sleep(scroll_pause_time)
  new_height = driver.execute_script("return document.body.scrollHeight")
  if new_height == last_height:
    break
  last_height = new_height

# 이미지 목록 불러오기
imgs = driver.find_elements(By.CSS_SELECTOR,
                            '._fe_image_tab_content_thumbnail_image')

# 폴더 생성
createFolder(folder_name)

# 엑셀 파일 초기화
wb_name = f"{input_name}_{current_time}.xlsx"
workbook = openpyxl.Workbook()
sheet = workbook.active
sheet.append(["이미지 이름", "Original URL", "이미지 URL"])


# 파일명에서 사용할 수 없는 문자를 제거하는 함수
def sanitize_filename(filename):
  invalid_chars = ["<", ">", ":", "\"", "/", "\\", "|", "?", "*"]
  for char in invalid_chars:
    filename = filename.replace(char, "")
  return filename[:250]


original_urls = set()  # 중복을 체크하기 위한 세트
idx = 0
image_data = []

while idx < len(driver.find_elements(By.CSS_SELECTOR,
                                     '._fe_image_tab_content_thumbnail_image')):
  imgs = driver.find_elements(By.CSS_SELECTOR,
                              '._fe_image_tab_content_thumbnail_image')
  img = imgs[idx]
  img_url = img.get_attribute('src')

  driver.execute_script("arguments[0].click();", img)
  try:
    link = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, '.info_area > a.info_title')))
    original_url = link.get_attribute('href')

    title_elem = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, 'a.info_title > strong.title')))
    title = sanitize_filename(title_elem.text.strip())

    file_name = f"{idx + 1}_{title}.jpg"
    file_path = os.path.join(folder_name, file_name)

    # 중복된 링크가 있는 경우 건너뛰기
    if original_url in original_urls:
      print(f"중복 URL 확인 : {original_url} / 이미지 이름 : {title}")
      image_data.append(
          [file_name, original_url, "중복으로 인해 저장되지 않음"])  # 중복된 이미지의 정보 저장
      driver.back()
      wait.until(EC.presence_of_all_elements_located(
          (By.CSS_SELECTOR, '._fe_image_tab_content_thumbnail_image')))
      idx += 1
      continue

    original_urls.add(original_url)  # 새로운 URL을 세트에 추가

  except Exception as e:
    print(f"Error for Image {idx + 1}: {str(e)}")
    original_url = None
    title = "Unknown"
    image_data.append(
        [f"{idx + 1}_Unknown.jpg", None, "오류로 인해 저장되지 않음"])  # 오류 발생시 정보 저장

  # 이미지 저장 로직 (중복되지 않은 경우에만 실행)
  if original_url:
    if img_url.startswith('data:image'):
      base64_data = img_url.split(",")[1]
      save_base64_image(base64_data, file_path)
    else:
      response = requests.get(img_url, stream=True)
      with open(file_path, 'wb') as file:
        for chunk in response.iter_content(1024):
          file.write(chunk)

    image_data.append([file_name, original_url, img_url])

  driver.back()
  wait.until(EC.presence_of_all_elements_located(
      (By.CSS_SELECTOR, '._fe_image_tab_content_thumbnail_image')))
  idx += 1

# 엑셀 데이터 한 번에 저장 (이미지 이름, 원본 URL, 이미지 URL 순)
for data in image_data:
  sheet.append([data[0], data[1], data[2]])
workbook.save(wb_name)

print(f'{input_name}의 이미지 및 URL 정보 수집 및 저장 작업 완료')
driver.quit()
