import os

import re

from collections import defaultdict

from pathlib import Path

import requests

import json

from bs4 import BeautifulSoup

from urllib.parse import urlparse

from PyPDF2 import PdfMerger

from config import DATA_DIR, ROOT_DIR

 

def build_fta_index(fta):

    index = {

        fta: {

            'chapter': {},

            'annex': {}

        }

    }

 

    # Build pdf_pages dict of chapters and annexes to then query one by one

 

    pdf_pages = dict()

   

    url = DATA_DIR[fta]['url']

    page = requests.get(url)

    soup = BeautifulSoup(page.content, 'html.parser')

 

    h_and_a = soup.find_all([re.compile('^h[1-6]$'), 'a'])

    chapter_flag = False

    annex_flag = False

 

    for ha in h_and_a:

        if ha.name[:1] == 'h':

            try:

                h_id = ha.attrs['id'].lower().strip()

            except KeyError:

                h_id = ''

       

            h_string = ha.string.lower().strip()

 

            if h_id[:7] == 'chapter' or h_string[:7] == 'chapter':

                pdf_pages['chapter'] = []

               chapter_flag = True

                annex_flag = False

                continue

 

            if h_id[:5] == 'annex' or h_string[:5] == 'annex':

                pdf_pages['annex'] = []

                annex_flag = True

                chapter_flag = False

                continue

 

            chapter_flag = False

            annex_flag = False

            continue

 

        if chapter_flag == True:

            if ha.name[:1] == 'a':

                pdf_pages['chapter'].append('https://www.gov.uk' + ha.attrs['href'])

 

        if annex_flag == True:

            if ha.name[:1] == 'a':

                pdf_pages['annex'].append('https://www.gov.uk' + ha.attrs['href'])

 

    # Iterate through pdf_pages dict and write the URLs to the index

 

    for section_type in pdf_pages:

        for pdf_url in pdf_pages[section_type]:

            pdf_page = requests.get(pdf_url)

            pdf_soup = BeautifulSoup(pdf_page.content, 'html.parser')

 

            fta_docs = pdf_soup.find('section', id=re.compile('^document')).find_all('a')

            for doc in fta_docs:

                doc_class = doc.get('class')

                doc_class = [] if doc_class == None else doc_class

                if 'thumbnail' not in doc_class:

                    doc_href = doc.get('href')

                    doc_filename = os.path.basename(urlparse(doc_href).path)

                    if doc_href.lower().endswith('.pdf'):

                        index[fta][section_type][doc.string] = {}

                        index[fta][section_type][doc.string]['url'] = doc_href

                        index[fta][section_type][doc.string]['local'] = \

                            os.path.join('data', fta, doc_filename)

 

    return index

 

 

def write_fta_index(fta, index):

    dl_dir = os.path.join(ROOT_DIR, 'data', fta)

    with open(os.path.join(dl_dir, fta + '.json'), 'w+') as f:

        json.dump(index, f)

 

 

def read_fta_index(fta):

    dl_dir = os.path.join(ROOT_DIR, 'data', fta)

    with open(os.path.join(dl_dir, fta + '.json'), 'r') as f:

        index = json.load(f)

    return index

 

 

def download_fta_pdfs(fta, index):

    fta_index = index[fta]

 

    for section_type in fta_index:

        for section in fta_index[section_type]:

            pdf = requests.get(fta_index[section_type][section]['url'])

            pdf_file = os.path.join(ROOT_DIR, Path(fta_index[section_type][section]['local']))

            with open(pdf_file, 'wb+') as f:

                f.write(pdf.content)

 

 

def merge_fta_pdfs(fta, index):

    # Merges PDFs, and returns the modified index to be saved

 

    fta_pdfs = []

 

    for section_type in index[fta]:

        if section_type in ['chapter', 'annex']:

            for section in index[fta][section_type]:

                fta_path = os.path.join(

                    ROOT_DIR,

                    Path(index[fta][section_type][section]['local'])

                )

                fta_pdfs.append(fta_path)

 

    index[fta]['full'] = 'data/' + fta + '/' '00_FULLTEXT_' + fta + '.pdf'

 

    merger = PdfMerger()

    for pdf in fta_pdfs:

        merger.append(pdf)

 

    pdf_file = os.path.join(ROOT_DIR, Path(index[fta]['full']))

 

    with open(pdf_file, 'wb+') as f:

        merger.write(f)

       

    merger.close()

 

    return index

 

 

if __name__ == '__main__':

    # (Re)Build indexes

    for fta_name in DATA_DIR:

        Path(os.path.join(ROOT_DIR, 'data', fta_name)).mkdir(parents=True, exist_ok=True)

        fta_index = build_fta_index(fta_name)

        write_fta_index(fta_name, fta_index)

   

    # (Re)Download PDFs

    for fta_name in DATA_DIR:

        Path(os.path.join(ROOT_DIR, 'data', fta_name)).mkdir(parents=True, exist_ok=True)

        fta_index = read_fta_index(fta_name)

        download_fta_pdfs(fta_name, fta_index)

   

    # (Re)Merge PDFs

    for fta_name in DATA_DIR:

        Path(os.path.join(ROOT_DIR, 'data', fta_name)).mkdir(parents=True, exist_ok=True)

        fta_index = read_fta_index(fta_name)

        fta_index_modified = merge_fta_pdfs(fta_name, fta_index)

        write_fta_index(fta_name, fta_index_modified)
