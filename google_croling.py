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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, \
  ElementClickInterceptedException

# 크롬 드라이버 설정 (오류 개선 및 운영 체제 호환성 고려)
service = ChromeService(ChromeDriverManager().install())

# Chrome Driver 옵션 설정
options = ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
# options.add_argument('--headless')  # 화면이 나오지 않고 크롤링(속도가 빠름)

# 웹드라이버 설정 및 페이지 접근
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 3)  # 10초 대기


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


# 파일명에서 사용할 수 없는 문자를 제거하는 함수
def sanitize_filename(filename):
  invalid_chars = ["<", ">", ":", "\"", "/", "\\", "|", "?", "*"]
  for char in invalid_chars:
    filename = filename.replace(char, "")
  return filename[:250]


# 검색어 입력
input_name = input('검색어 입력: ').strip().replace('/', '_').replace('\\', '_')
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
folder_name = f"{input_name}_{current_time}"

try:
  # 구글 이미지 검색 페이지로 이동
  driver.get(f'https://www.google.com/search?tbm=isch&q={input_name}')
  wait.until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'img.YQ4gaf')))

  # 스크롤 다운을 통해 이미지 로드
  scroll_pause_time = 2
  last_height = driver.execute_script("return document.body.scrollHeight")

  while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(scroll_pause_time)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
      try:
        # "더 보기" 버튼 클릭
        load_more_button = driver.find_element(By.CSS_SELECTOR, ".mye4qd")
        driver.execute_script("arguments[0].click();", load_more_button)
        time.sleep(scroll_pause_time)
      except (NoSuchElementException, ElementClickInterceptedException):
        print("더 이상 로드할 이미지가 없습니다.")
        break
    last_height = new_height

  # 이미지 목록 불러오기
  imgs = driver.find_elements(By.CSS_SELECTOR, 'img.YQ4gaf')
  print(f"총 {len(imgs)}개의 이미지 찾음.")

  # 폴더 생성
  createFolder(folder_name)

  # 엑셀 파일 초기화
  wb_name = f"{input_name}_{current_time}.xlsx"
  workbook = openpyxl.Workbook()
  sheet = workbook.active
  sheet.append(["이미지 이름", "이미지 URL"])

  image_data = []
  total_images = len(imgs)
  max_images = 100  # 다운로드할 최대 이미지 수 설정 (필요시 조정)

  for idx in range(min(total_images, max_images)):
    try:
      img = imgs[idx]
      img_url = img.get_attribute('src')

      # 파일명 생성 (인덱스를 기반으로 고유한 이름 부여)
      file_name = f"{idx + 1}.jpg"
      file_path = os.path.join(folder_name, file_name)

      # 이미지 저장 로직
      if img_url.startswith('data:image'):
        base64_data = img_url.split(",")[1]
        save_base64_image(base64_data, file_path)
      else:
        response = requests.get(img_url, stream=True, timeout=10)
        if response.status_code == 200:
          with open(file_path, 'wb') as file:
            for chunk in response.iter_content(1024):
              file.write(chunk)
        else:
          print(f"이미지 {idx + 1} 다운로드 실패: HTTP {response.status_code}")
          image_data.append([file_name, "다운로드 실패"])
          continue

      image_data.append([file_name, img_url])
      print(f"이미지 {idx + 1} 저장 완료: {file_name}")

    except Exception as e:
      print(f"이미지 {idx + 1} 저장 중 오류 발생: {str(e)}")
      image_data.append([f"{idx + 1}_Unknown.jpg", "오류로 인해 저장되지 않음"])
      continue

  # 엑셀 데이터 저장 (이미지 이름, 이미지 URL 순)
  for data in image_data:
    sheet.append([data[0], data[1]])
  workbook.save(wb_name)

  print(f'{input_name}의 이미지 및 URL 정보 수집 및 저장 작업 완료')

except KeyboardInterrupt:
  print("크롤링이 사용자에 의해 중단되었습니다.")
except Exception as e:
  print(f"예기치 않은 오류 발생: {str(e)}")
finally:
  driver.quit()
