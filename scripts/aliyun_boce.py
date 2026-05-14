import re
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# CONFIG

test_url = "https://appapi.gtjai.com/xxl-job-admin/toLogin"
download_dir = Path(__file__).parent.joinpath("boce_report")
download_dir.mkdir(parents=True, exist_ok=True)

# ====================== 初始化浏览器 ======================
options = webdriver.EdgeOptions()
# options.add_argument("--start-maximized")  # 窗口最大化，避免元素点击失效
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
# options.add_experimental_option("excludeSwitches", ["enable-logging"])  # 关闭无用日志
options.add_argument("--enable-bidi")  # 开启 BiDi
options.set_capability("webSocketUrl", True)
options.enable_bidi = True
options.add_experimental_option("prefs", {"download.default_directory": str(download_dir)})

driver = webdriver.Edge(options=options)
wait = WebDriverWait(driver, 120)  # 最多等待20秒
network = driver.network
driver.execute_cdp_cmd("Network.enable", {})

result_json = {}

try:
    driver.get("https://boce.aliyun.com/detect/http")
    print("✅ 已打开阿里云检测页面")
    # ============== 2. 点击展开菜单 ==============
    expand_selector = "#cms-console-one-probe > div > div.cms_container > div:nth-child(3) > div.search-tab > div > div.next-tabs-content > div > div > form > div:nth-child(1) > div.input-area.false > span:nth-child(1) > span > span.next-input.next-medium.next-select-inner > span.next-input-control > span > i"
    expand_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, expand_selector))
    )
    expand_btn.click()
    print("✅ 已点击展开菜单")
    time.sleep(0.5)

    # ============== 3. 选中【境外】 ==============
    overseas_selector = "#area > label:nth-child(8) > span.next-checkbox > input"
    # overseas_checkbox = wait.until(
    #     EC.element_to_be_clickable((By.CSS_SELECTOR, overseas_selector))
    # )
    overseas_checkbox = driver.find_element(By.CSS_SELECTOR, overseas_selector)
    # overseas_checkbox.click()
    driver.execute_script("arguments[0].click();", overseas_checkbox)  # 防止被覆盖点击失败
    print("✅ 已选中【境外】")
    time.sleep(0.5)

    # ============== 4. 点击【确认】 ==============
    confirm_selector = "#cms-console-one-probe > div > div.cms_container > div:nth-child(3) > div.search-tab > div > div.next-tabs-content > div > div > form > div:nth-child(1) > div.input-area.false > div > div > div > div > button.next-btn.next-medium.next-btn-primary.on-ok-button > span"
    confirm_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, confirm_selector))
    )
    confirm_btn.click()
    print("✅ 已点击确认")
    time.sleep(0.5)

    # ============== 5. 输入 qq.com ==============
    input_selector = "#url1"
    input_box = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, input_selector))
    )
    input_box.clear()
    input_box.send_keys(test_url)
    print(f"✅ 已输入 {test_url}")

    # ============== 6. 点击检测按钮 ==============
    detect_btn_selector = "#cms-console-one-probe > div > div.cms_container > div:nth-child(3) > div.search-tab > div > div.next-tabs-content > div > div > form > div:nth-child(1) > div.button-group > button.next-btn.next-large.next-btn-primary.pramary-button"
    detect_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, detect_btn_selector))
    )
    detect_btn.click()
    print("✅ 已点击开始检测")

    # ============== 7. 等待结果出现 ==============
    result_wait_selector = "#cms-console-one-probe > div > div.cms_container > div:nth-child(3) > div:nth-child(2) > div > div > div.round-info > div.next-row.detection-res > div.next-col.next-col-9 > span.share-link"
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, result_wait_selector))
    )
    print("✅ 检测完成，结果已加载")

    # ============== 8. 点击最终按钮 ==============
    time.sleep(1)
    final_btn_selector = "#cms-console-one-probe > div > div.cms_container > div:nth-child(3) > div:nth-child(2) > div > div > div.ping-result-area > button"
    final_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, final_btn_selector)),
        message="最终按钮未找到",
    )
    final_btn.click()
    print("✅ 已点击最终按钮，脚本执行完成！")
    time.sleep(10)

    # 重命名下载的文件
    file = download_dir.joinpath(re.sub(r'[:/&?]', "_", test_url) + '-http-result.xlsx')
    if file.exists():
        file.rename(file.with_name(file.stem + time.strftime("%Y%m%d%H%M%S") + ".xlsx"))
        file.with_stem()
        print("✅ 已重命名下载文件")
    else:
        print(f"❌ 未找到下载文件: {file}")
        download_dir.iterdir()


except Exception as e:
    print("❌ 执行出错：", e)

finally:
    # 停留查看结果
    time.sleep(5)
    driver.quit()

