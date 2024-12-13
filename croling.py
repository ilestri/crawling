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


# 검색 엔진 선택
print("검색 엔진 선택:")
print("1. 네이버")
print("2. 구글")
engine_choice = input("원하는 검색 엔진의 번호를 입력하세요 (1 또는 2): ").strip()

if engine_choice == '1':
  search_engine = 'naver'
elif engine_choice == '2':
  search_engine = 'google'
else:
  print("잘못된 선택입니다. 기본값으로 네이버를 사용합니다.")
  search_engine = 'naver'

# 검색어 입력
input_name = input('검색어 입력: ').strip().replace('/', '_').replace('\\', '_')
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
folder_name = f"{input_name}_{current_time}"

try:
  if search_engine == 'naver':
    # 네이버 이미지 검색 URL
    search_url = f'https://search.naver.com/search.naver?where=image&sm=tab_jum&query={input_name}'
    driver.get(search_url)
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

  elif search_engine == 'google':
    # 구글 이미지 검색 URL
    search_url = f'https://www.google.com/search?tbm=isch&q={input_name}'
    driver.get(search_url)
    wait.until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, 'img.YQ4gaf')))

    # 스크롤 다운 및 더 보기 클릭
    scroll_pause_time = 2
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
      driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
      time.sleep(scroll_pause_time)
      # "더 보기" 버튼 클릭 시도
      try:
        load_more = driver.find_element(By.CSS_SELECTOR, ".mye4qd")
        driver.execute_script("arguments[0].click();", load_more)
        time.sleep(scroll_pause_time)
      except:
        pass  # 더 이상 "더 보기" 버튼이 없을 경우 무시

      new_height = driver.execute_script("return document.body.scrollHeight")
      if new_height == last_height:
        break
      last_height = new_height

    # 이미지 목록 불러오기
    imgs = driver.find_elements(By.CSS_SELECTOR, 'img.Q4LuWd')

  else:
    raise ValueError("지원되지 않는 검색 엔진입니다.")

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
    if search_engine == 'naver':
      imgs = driver.find_elements(By.CSS_SELECTOR,
                                  '._fe_image_tab_content_thumbnail_image')
      if idx >= len(imgs):
        print(f"총 {idx}개의 이미지를 처리했습니다.")
        break
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

    elif search_engine == 'google':
      imgs = driver.find_elements(By.CSS_SELECTOR, 'img.Q4LuWd')
      if idx >= len(imgs):
        print(f"총 {idx}개의 이미지를 처리했습니다.")
        break
      img = imgs[idx]
      img_url = img.get_attribute('src')

      try:
        driver.execute_script("arguments[0].click();", img)
      except Exception as e:
        print(f"이미지 클릭 오류 {idx + 1}: {str(e)}")
        image_data.append(
            [f"{idx + 1}_Unknown.jpg", None, "클릭 오류로 인해 저장되지 않음"])
        idx += 1
        continue

      try:
        # 원본 이미지 URL 가져오기
        original_url = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'a.eHAdSb'))).get_attribute('href')

        title = sanitize_filename(input_name)

        file_name = f"{idx + 1}_{title}.jpg"
        file_path = os.path.join(folder_name, file_name)

        # 중복된 링크가 있는 경우 건너뛰기
        if original_url in original_urls:
          print(f"중복 URL 확인 : {original_url} / 이미지 이름 : {title}")
          image_data.append(
              [file_name, original_url, "중복으로 인해 저장되지 않음"])  # 중복된 이미지의 정보 저장
          driver.execute_script("window.history.go(-1)")
          wait.until(EC.presence_of_all_elements_located(
              (By.CSS_SELECTOR, 'img.Q4LuWd')))
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
      try:
        if img_url.startswith('data:image'):
          base64_data = img_url.split(",")[1]
          save_base64_image(base64_data, file_path)
        else:
          response = requests.get(img_url, stream=True)
          if response.status_code == 200:
            with open(file_path, 'wb') as file:
              for chunk in response.iter_content(1024):
                file.write(chunk)
          else:
            print(
              f"Failed to download image {idx + 1}: HTTP {response.status_code}")
            image_data.append([file_name, original_url, "이미지 다운로드 실패"])
            if search_engine == 'naver':
              driver.back()
            elif search_engine == 'google':
              driver.execute_script("window.history.go(-1)")
            wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR,
                 'img.Q4LuWd' if search_engine == 'google' else '._fe_image_tab_content_thumbnail_image')))
            idx += 1
            continue

        image_data.append([file_name, original_url, img_url])
        print(f"이미지 {idx + 1} 저장 완료: {file_name}")

      except Exception as e:
        print(f"Error saving Image {idx + 1}: {str(e)}")
        image_data.append([file_name, original_url, "저장 중 오류 발생"])

    if search_engine == 'naver':
      driver.back()
      wait.until(EC.presence_of_all_elements_located(
          (By.CSS_SELECTOR, '._fe_image_tab_content_thumbnail_image')))
    elif search_engine == 'google':
      driver.execute_script("window.history.go(-1)")
      wait.until(EC.presence_of_all_elements_located(
          (By.CSS_SELECTOR, 'img.Q4LuWd')))
    idx += 1

  # 엑셀 데이터 한 번에 저장 (이미지 이름, 원본 URL, 이미지 URL 순)
  for data in image_data:
    sheet.append([data[0], data[1], data[2]])
  workbook.save(wb_name)

  print(f'{input_name}의 이미지 및 URL 정보 수집 및 저장 작업 완료')
finally:
  driver.quit()
