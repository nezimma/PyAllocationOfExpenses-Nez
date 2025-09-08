# -*- coding: cp1251 -*-
import time
import os
import pyperclip
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import subprocess
import requests

url = 'https://www.relax.by/cat/ent/restorans/'

chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
params = [
    chrome_path,
    "--remote-debugging-port=9222",
    r"--user-data-dir=C:\\selenum\\ChromeProfile"
]

def parswebsite(url):








# df = pd.DataFrame(columns=['num', 'url', 'title', 'category', 'data'])
# df.to_csv('DatasetK')

