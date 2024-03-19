import os
import redis
import re
from bs4 import BeautifulSoup

r = redis.StrictRedis()

def load_dir(path):         
    files = os.listdir(path)         
    for f in files:             
        match = re.match(r"book(\d+).html$", f)             
        if match is not None:                 
            with open(path + f) as file:                     
                html = file.read()                     
                book_id = match.group(1)
                create_index(book_id, html)
                r.set(f"book: {book_id}", html)
                print(f"file {file} loaded into redis...")

def create_index(book_id, html):
    soup = BeautifulSoup(html, 'html.parser')
    ts = soup.get_text().split(' ')
    for term in ts:
        r.sadd(term, book_id)

load_dir("html/books/")
