# -*- coding: cp1251 -*-
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import pandas as pd
from selenium import webdriver
import time
from g4f.client import Client

url_relaxBy = 'https://www.relax.by/cat/ent/restorans/'
url_edaRu= 'https://eda.ru/recepty?page=2'
url_poduct= 'https://fitaudit.ru/food/abc'
url_restoplaceCC = "https://restoplace.cc/blog/organizaciya-dostavki-edy"
url_obsch = 'https://money.onliner.by/tag/obshhestvennyj-transport'
url_taxi = 'https://auto.onliner.by/tag/taksi'
url_karsh = 'https://auto.onliner.by/tag/karshering'
url_globalAutoBy = 'https://auto.onliner.by/world'
url_AZS = 'https://officelife.media/article/41922-kak-podelen-rynok-azs-v-belarusi/'
url_poezda = 'https://people.onliner.by/tag/poezda'
url_avia = 'https://people.onliner.by/tag/aviaciya'
url_kikshering = 'https://auto.onliner.by/tag/kikshering'
url = 'https://www.spr.by/otzyvy/'


chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
params = [
    chrome_path,
    "--remote-debugging-port=9222",
    r"--user-data-dir=C:\\selenum\\ChromeProfile"
]

def parswebsite(url):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(1)
    click_cookes = driver.find_element(by=By.XPATH, value='//button[@class="Button Button--big Button--primary Button--rounded"]')
    click_cookes.click()
    a_link = parse_list(driver)
    print(a_link)
    for i in a_link:
        time.sleep(1)
        driver.execute_script("arguments[0].click();", i)
        time.sleep(5)
        parse_list(driver)
def parse_list(driver):
    for i in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
    titles = driver.find_elements(by=By.XPATH, value='//div[@class="PlaceList__itemWrapper--content"]')
    time.sleep(7)
    for i in titles:
        div_site = i.find_element(by=By.XPATH, value='.//div[@class="Place__mainTitle"]')
        a_element = div_site.find_element(By.TAG_NAME, 'a')
        link = a_element.get_attribute('href')
        main_text = i.find_element(by=By.XPATH, value='.//div[@class="Place__description h6 small"]')
        print(f'{link}       {div_site.text[4:]}       Ресторан и еда       {main_text.text}')
        new_data = {
            'url': link,
            'title': div_site.text[4:],
            'category': 'Ресторан и еда',
            'data': main_text.text
        }
        df_new = pd.DataFrame([new_data])
        df_new.to_csv('DatasetK.csv', mode='a', header=False, index=True, sep='|', encoding='utf-8')
    div_link_site = driver.find_element(by=By.XPATH, value='//div[@class="Pagination__listPages"]')
    link_site = div_link_site.find_elements(By.TAG_NAME, 'a')
    link_site.pop(0)
    return link_site

    #39 строк

def pars_edaRu(url):
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 5)  # Ожидание до 10 секунд
    driver.get(url)
    for i in range(1000):
        driver.execute_script(f"window.scrollTo(0, 1000);")
        scroll = 1000
        step = 250
        for j in range(i):
            scroll += step
            driver.execute_script(f"window.scrollTo(0, {scroll});")
            time.sleep(1)
        open_resept(driver, wait, i, url)

def open_resept(driver, wait, fir_num, base_url):
    try:
        # Ожидаем загрузки контента
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='css-1j5xcrd']")))
        except TimeoutException:
            print("Таймаут ожидания элементов контента")
            return False

        if "data;" in driver.page_source:
            print("Обнаружен 'data;' в open_resept")
            return False

        # Поиск элементов с ожиданием
        div_element_main_site = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[@class='css-1j5xcrd']"))
        )
        print(f"Найдено элементов: {len(div_element_main_site)}")

        if fir_num >= len(div_element_main_site):
            print(f"Индекс {fir_num} превышает количество элементов")
            return False

        # Прокручиваем и кликаем с ожиданием кликабельности
        element = wait.until(EC.element_to_be_clickable(div_element_main_site[fir_num]))
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(1)
        element.click()

        # Ожидаем загрузки страницы рецепта
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='css-1h7uuyv']")))
        except TimeoutException:
            print("Таймаут загрузки страницы рецепта")
            driver.get(base_url)
            time.sleep(3)
            return False

        # Проверка после клика
        if "data;" in driver.page_source:
            print("Обнаружен 'data;' после клика")
            driver.get(base_url)
            time.sleep(3)
            return False

        # Извлечение данных с ожиданием
        title = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='css-1h7uuyv']")))
        print(title.text)

        text = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'css-aiknw3')))
        link = driver.current_url

        new_data = {
            'url': link,
            'title': title.text,
            'category': 'Ресторан и еда',
            'data': text.text
        }

        print(f"{link} | {title.text} | Ресторан и еда")
        df_new = pd.DataFrame([new_data])
        df_new.to_csv('DatasetK.csv', mode='a', header=False, index=True, sep='|', encoding='utf-8')

        # Возврат на основную страницу
        driver.get(base_url)

        # Ожидаем загрузки основной страницы
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='css-1j5xcrd']")))
        time.sleep(2)

        return True

    except TimeoutException:
        print("Таймаут в open_resept")
        driver.get(base_url)
        time.sleep(3)
        return False
    except NoSuchElementException:
        print("Элемент не найден в open_resept")
        driver.get(base_url)
        time.sleep(3)
        return False
    except StaleElementReferenceException:
        print("Элемент устарел в open_resept")
        driver.get(base_url)
        time.sleep(3)
        return False
    except Exception as e:
        print(f"Ошибка в open_resept: {str(e)}")
        driver.get(base_url)
        time.sleep(3)
        return False

#c 40 до 272

def parse_green(url):
    driver = webdriver.Chrome()
    driver.get(url)
    mass_text = []
    mass_url = []
    time.sleep(5)
    all_letter = driver.find_elements(By.CSS_SELECTOR, ".fimlist.fimlist__items")
    for i in all_letter:
        tovar = i.find_elements(by=By.CLASS_NAME, value='vertical_pseudo')
        for j in tovar:
            mass_text.append(j.text)
    mass = [product.split('\n') for product in mass_text]

    def normalize(word):
        if word.lower() == 'шоколадный':
            return word.lower()  # исключение - не меняем
        if word.endswith('ы'):
            return word[:-1].lower()
        return word.lower()

    seen = set()
    result = []

    for item in mass:
        first_word = item[0].split()[0]
        key = normalize(first_word)
        if key not in seen:
            seen.add(key)
            result.append(item)

    client = Client()
    for i in range(348, len(result)): #987
        time.sleep(3)
        print(result[i])
        title = result[i][0]
        question = f'напиши кратко что такое {title}, нужно описать как для сбора информации для датасета на тему рестораны и еда, не более 60 слов'
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content':f'{question}'}],
            web_search=False
        )
        data = response.choices[0].message.content.replace('\n', ' ')
        print(data)

        new_data = {
            'url': 'https://fitaudit.ru/food/abc',
            'title': title,
            'category': 'Ресторан и еда',
            'data': data.replace('**', '')
        }

        print(f"'https://fitaudit.ru/food/abc' | {title} | Ресторан и еда")
        df_new = pd.DataFrame([new_data])
        df_new.to_csv('DatasetK.csv', mode='a', header=False, index=True, sep='|', encoding='utf-8')
        time.sleep(2)

def parse_delivery(url):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(5)
    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight);")
    all_text = driver.find_elements(by=By.XPATH, value='//div[@class="t-text t-text_md "]')
    print(all_text)
    results = []
    time.sleep(1)
    print(len(all_text))
    for i in all_text:
        print(i.text)
        frase = i.text.split('.')
        for idx, sentence in enumerate(frase):
            if "доставк" in sentence.lower():
                # записываем текущее предложение и следующее (если есть)
                next_sentence = frase[idx + 1] if idx + 1 < len(frase) else ''
                results.append(sentence.strip() + '.' + ' ' + next_sentence.strip())
                print(results)
    time.sleep(1)
    for i in results:
        new_data = {
            'url': 'https://fitaudit.ru/food/abc',
            'title': 'Доставка',
            'category': 'Ресторан и еда',
            'data': i
        }
        df_new = pd.DataFrame([new_data])
        df_new.to_csv('DatasetK.csv', mode='a', header=False, index=True, sep='|', encoding='utf-8')


def pars_onliner(url):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(2)
    for i in range(40):
        time.sleep(2)
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight);")
        print(i//8)
        if i // 8 >=1:
            for j in range(i//8):
                click_next = driver.find_element(by=By.XPATH, value='//div[@class="news-more__control"]')
                click_next.click()
                time.sleep(1)
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
        element_news = driver.find_elements(by=By.XPATH, value='//div[@class="news-tidings__item news-tidings__item_1of3 news-tidings__item_condensed "]')
        element_news[i].click()
        time.sleep(2)
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        div_p = driver.find_element(by=By.XPATH, value='//div[@class="news-text"]')
        arg_p = div_p.find_elements(by=By.TAG_NAME, value='p')
        for i in arg_p:
            count = i.text.count('.')
            if count >=2 and 'анонимно' not in i.text:
                title = driver.find_element(by=By.XPATH, value='//div[@class="news-header__title"]')
                new_data = {
                    'url': driver.current_url,
                    'title': title.text,
                    'category': 'Транспорт',
                    'data': i.text
                }

                print(f"{driver.current_url} | {title.text} | Транспорт")
                df_new = pd.DataFrame([new_data])
                df_new.to_csv('DatasetK.csv', mode='a', header=False, index=True, sep='|', encoding='utf-8')
        driver.back()

def pars_AZS(url):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(2)
    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight);")
    all_text = driver.find_element(by=By.XPATH, value='//div[@class="article__content"]')
    arg_p = all_text.find_elements(by=By.TAG_NAME, value='p')
    for i in arg_p:
        count = i.text.count('.')
        if count >= 2 and 'анонимно' not in i.text:
            title = driver.find_element(by=By.XPATH, value='//div[@class="article__title"]')
            new_data = {
                'url': driver.current_url,
                'title': title.text,
                'category': 'Транспорт',
                'data': i.text
            }

            print(f"{driver.current_url} | {title.text} | Транспорт")
            df_new = pd.DataFrame([new_data])
            df_new.to_csv('DatasetK.csv', mode='a', header=False, index=True, sep='|', encoding='utf-8')



mass = ['']

def pars_review(url):
    try:
        driver = webdriver.Chrome()
        driver.get(url)
        time.sleep(5)
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight);")
        print('.')
        for i in mass:
            superM = driver.find_element(By.XPATH, f'//a[@title="{i}"]')
            superM.click()
            time.sleep(1)
            organization = driver.find_elements(By.XPATH, '//div[@class="itemFlexInfo"]')
            main_window = driver.current_window_handle
            for j in organization:
                j.click()
                time.sleep(1)
                all_windows = driver.window_handles
                for window in all_windows:
                    if window != main_window:
                        driver.switch_to.window(window)
                        break
                rew = driver.find_element(By.XPATH, '//nav[@class="middleMenuDefault"]')
                li_arg = rew.find_elements(By.TAG_NAME, 'li')
                li_arg[1].click()
                time.sleep(1)
                driver.fullscreen_window()
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight);")
                hh = driver.find_element(By.XPATH, '//a[@class="btnLoad"]')
                print(hh)
                time.sleep(3)
                hh.click()

                for u in range(10):
                    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                block_text = driver.find_elements(By.XPATH, '//div[@class="review reviewPositive"]')
                block_text1 = driver.find_elements(By.XPATH, '//div[@class="review reviewNegative"]')
                block_text = block_text+block_text1
                for y in block_text:
                    title = y.find_element(By.XPATH, '//div[@class="reviewTitleText"]').text
                    # try:
                    #     element = driver.find_element(By.XPATH, "//a[@data-readmore and contains(@class, 'linkFullText') and contains(@class, 'readMoreReview') and text()='читать  полностью']")
                    #     element.click()
                    #     time.sleep(2)
                    #     text = driver.find_element(By.CLASS_NAME, 'popupReviewsText')
                    #     close = driver.find_element(By.CLASS_NAME, 'popupContainerClose')
                    #     time.sleep(3)
                    #     close.click()
                    # except Exception as e:
                    text = y.find_element(By.CLASS_NAME, 'reviewText').text.replace('читать полностью','')
                    point = text.count('.')
                    main_url = driver.current_url
                    if point >3:
                        # тут написать код записи
                        new_data = {
                            'url': driver.current_url,
                            'title': title,
                            'category': 'Ресторан и еда',
                            'data': text
                        }

                        df_new = pd.DataFrame([new_data])
                        df_new.to_csv('DatasetK.csv', mode='a', header=False, index=True, sep='|', encoding='utf-8')
                        print(main_url,'|',title,'|','Рестораны и еда|',text)
                driver.close()
                driver.switch_to.window(main_window)
            driver.back()
    except Exception as e:
        print(e)
        time.sleep(100)



def main():
    pars_review(url)

if __name__ == '__main__':
    main()



# df = pd.DataFrame(columns=['num', 'url', 'title', 'category', 'data'])
# df.to_csv('DatasetK')

