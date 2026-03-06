#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 28 12:08:18 2024

@author: michaelwai
"""
# https://13f.info/13f/000090514824000751-scion-asset-management-llc-q4-2023-restatement
# Michael burry CIK 0001649339
# https://13f.info/manager/0001067983-berkshire-hathaway-inc
# Warren Buffet 0001067983

from unicodedata import name
import pandas as pd
import requests
import re
import csv
import lxml
from bs4 import BeautifulSoup
import warnings
from bs4 import GuessedAtParserWarning
import time
warnings.filterwarnings('ignore', category=GuessedAtParserWarning)

sec_url = 'https://www.sec.gov'

def get_request(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br',
        'HOST': 'www.sec.gov',
    }
    
    headers = {
     'User-Agent': 'michael lae michael@email.com',
     'Accept-Encoding': 'gzip, deflate',
     'Host': 'www.sec.gov'
    }
        
    # headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36' ,'HOST': 'www.sec.gov'}
    print(f'requestiing {url} and wait 3 sec...')
    time.sleep(3)
    return requests.get(url, headers=headers)

def create_url(cik):
    url= 'https://www.sec.gov/cgi-bin/browse-edgar?CIK={}&owner=exclude&action=getcompany&type=13F-HR'.format(cik)
    print (url)
    return url

def get_user_input():
    cik = input("Enter 10-digit CIK number: ")
    return cik


def scrap_company_report(requested_cik):
    # Find mutual fund by CIK number on EDGAR
    response = get_request(create_url(requested_cik))
    soup = BeautifulSoup(response.text, "html.parser")
    tags = soup.findAll('a', id="documentsbutton")
    last_report = (sec_url + tags[0]['href'])
    previous_report = (sec_url + tags[1]['href'])
    scrap_report_by_url(last_report, "last_report")
    scrap_report_by_url(previous_report, "previous_report")


def scrap_report_by_url(url, filename):
    response_two = get_request(url)
    soup_two = BeautifulSoup(response_two.text, "html.parser")
    tags_two = soup_two.findAll('a', attrs={'href': re.compile('xml')})
    xml_url = tags_two[3].get('href')

    response_xml = get_request(sec_url + xml_url)
    soup_xml = BeautifulSoup(response_xml.content,"lxml")
    xml_to_csv(soup_xml, filename)


def xml_to_csv(soup_xml, name):

    columns = [
        "Name of Issuer",
        "CUSIP",
        "Value (x$1000)",
        "Shares",
        "Investment Discretion",
        "Voting Sole / Shared / None"
    ]
    issuers = soup_xml.body.findAll(re.compile('nameofissuer'))
    cusips = soup_xml.body.findAll(re.compile('cusip'))
    values = soup_xml.body.findAll(re.compile('value'))
    sshprnamts = soup_xml.body.findAll('sshprnamt')
    sshprnamttypes = soup_xml.body.findAll(re.compile('sshprnamttype'))
    investmentdiscretions = soup_xml.body.findAll(re.compile('investmentdiscretion'))
    soles = soup_xml.body.findAll(re.compile('sole'))
    shareds = soup_xml.body.findAll(re.compile('shared'))
    nones = soup_xml.body.findAll(re.compile('none'))

    df = pd.DataFrame(columns= columns)

    for issuer, cusip, value, sshprnamt, sshprnamttype, investmentdiscretion, sole, shared, none in zip(issuers, cusips, values, sshprnamts, sshprnamttypes, investmentdiscretions, soles, shareds, nones):
        row = pd.DataFrame(
            {
            "Name of Issuer": issuer.text,
            "CUSIP": cusip.text,
            "Value (x$1000)": value.text,
            "Shares": f"{sshprnamt.text} {sshprnamttype.text}",
            "Investment Discretion": investmentdiscretion.text,
            "Voting Sole / Shared / None": f"{sole.text} / {shared.text} / {none.text}"
            }, index=[0]
        )
        df = pd.concat([df,row])

    for i, name in enumerate(df["Name of Issuer"].unique(), 1):
        print(f"{i}. {name}")    
    
    print ('saved to ','./'+f"{requested_cik}.csv")
    df.to_csv('./'+f"{requested_cik}.csv")


requested_cik = get_user_input()
scrap_company_report(requested_cik)
