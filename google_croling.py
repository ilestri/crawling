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

# 크롬 드라이버 설정 (오류 개선 및 운영 체제 호환성 고려)
service = ChromeService(ChromeDriverManager().install())

# Chrome Driver 옵션 설정
options = ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
# options.add_argument('--headless')  # 화면이 나오지 않고 크롤링(속도가 빠름)

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
  wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'img.YQ4gaf')))

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
      except Exception:
        break
    last_height = new_height

  # 이미지 목록 불러오기
  imgs = driver.find_elements(By.CSS_SELECTOR, 'img.YQ4gaf')

  # 폴더 생성
  createFolder(folder_name)

  # 엑셀 파일 초기화
  wb_name = f"{input_name}_{current_time}.xlsx"
  workbook = openpyxl.Workbook()
  sheet = workbook.active
  sheet.append(["이미지 이름", "Original URL", "이미지 URL"])

  original_urls = set()  # 중복을 체크하기 위한 세트
  idx = 0
  image_data = []
  total_images = len(imgs)
  max_images = 100  # 다운로드할 최대 이미지 수 설정 (필요시 조정)

  while idx < total_images and idx < max_images:
    imgs = driver.find_elements(By.CSS_SELECTOR, 'img.YQ4gaf')
    if idx >= len(imgs):
      print(f"총 {idx}개의 이미지를 처리했습니다.")
      break
    img = imgs[idx]
    img_url = img.get_attribute('src')

    try:
      driver.execute_script("arguments[0].click();", img)
    except Exception as e:
      print(f"이미지 {idx + 1} 클릭 실패: {str(e)}")
      idx += 1
      continue

    try:
      # 큰 이미지가 로드될 때까지 대기
      wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'img.sFlh5c')))
      large_imgs = driver.find_elements(By.CSS_SELECTOR, 'img.sFlh5c')
      large_img_url = None
      for large_img in large_imgs:
        src = large_img.get_attribute('src')
        if src and 'http' in src:
          large_img_url = src
          break

      if not large_img_url:
        print(f"이미지 {idx + 1}의 URL을 찾을 수 없습니다.")
        image_data.append([f"{idx + 1}_Unknown.jpg", None, "URL을 찾을 수 없음"])
        idx += 1
        driver.execute_script("window.history.go(-1)")
        continue

      # 이미지의 원본 URL을 찾기 위해 'Visit' 버튼 클릭
      try:
        visit_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@href and contains(text(),"Visit")]')))
        original_url = visit_button.get_attribute('href')
      except Exception:
        original_url = "원본 URL을 찾을 수 없음"

      # 제목 추출 (가능한 경우)
      try:
        title_elem = driver.find_element(By.CSS_SELECTOR, 'div.eFM0qc')
        title = sanitize_filename(title_elem.text.strip())
        if not title:
          title = "Unknown"
      except Exception:
        title = "Unknown"

      file_name = f"{idx + 1}_{title}.jpg"
      file_path = os.path.join(folder_name, file_name)

      # 중복된 원본 URL 체크
      if original_url in original_urls:
        print(f"중복 URL 확인 : {original_url} / 이미지 이름 : {title}")
        image_data.append([file_name, original_url, "중복으로 인해 저장되지 않음"])
        idx += 1
        driver.execute_script("window.history.go(-1)")
        continue

      original_urls.add(original_url)  # 새로운 URL을 세트에 추가

    except Exception as e:
      print(f"Error for Image {idx + 1}: {str(e)}")
      original_url = None
      title = "Unknown"
      image_data.append([f"{idx + 1}_Unknown.jpg", None, "오류로 인해 저장되지 않음"])
      idx += 1
      driver.execute_script("window.history.go(-1)")
      continue

    # 이미지 저장 로직 (중복되지 않은 경우에만 실행)
    if large_img_url:
      try:
        if large_img_url.startswith('data:image'):
          base64_data = large_img_url.split(",")[1]
          save_base64_image(base64_data, file_path)
        else:
          response = requests.get(large_img_url, stream=True)
          if response.status_code == 200:
            with open(file_path, 'wb') as file:
              for chunk in response.iter_content(1024):
                file.write(chunk)
          else:
            print(f"Failed to download image {idx + 1}: HTTP {response.status_code}")
            image_data.append([file_name, original_url, "이미지 다운로드 실패"])
            idx += 1
            driver.execute_script("window.history.go(-1)")
            continue

        image_data.append([file_name, original_url, large_img_url])
        print(f"이미지 {idx + 1} 저장 완료: {file_name}")

      except Exception as e:
        print(f"Error saving Image {idx + 1}: {str(e)}")
        image_data.append([file_name, original_url, "저장 중 오류 발생"])

    driver.execute_script("window.history.go(-1)")
    time.sleep(1)  # 잠시 대기
    idx += 1

  # 엑셀 데이터 한 번에 저장 (이미지 이름, 원본 URL, 이미지 URL 순)
  for data in image_data:
    sheet.append([data[0], data[1], data[2]])
  workbook.save(wb_name)

  print(f'{input_name}의 이미지 및 URL 정보 수집 및 저장 작업 완료')
finally:
  driver.quit()
