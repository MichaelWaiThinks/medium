#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 24 01:03:34 2024

@author: michaelwai
"""
from numerize_denumerize import numerize, denumerize
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF

# Provided data
# df = pd.read_csv('WMT_balance_sheet.csv')
# =============================================================================
# print(data)
# aaa
# data = {
#     'asOfDate': ['2021-01-31', '2022-01-31', '2023-01-31'],
#     'AccountsPayable': [49141000000.0, 55261000000.0, 53742000000.0],
#     'AccountsReceivable': [6516000000.0, 8280000000.0, 7933000000.0],
#     'Inventory': [44949000000.0, 56511000000.0, 56576000000.0],
#     # Add other financial data here...
# }
# 
# # Create DataFrame
# df = pd.DataFrame(data)
# =============================================================================

data=pd.read_csv('WMT_balance_sheet.csv').to_dict()
df = pd.DataFrame(data)

# Set 'asOfDate' as index
df.set_index('asOfDate', inplace=True)

import pandas as pd
from fpdf import FPDF


# Extract years
years = df.columns.tolist()

# Initialize PDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Function to add a chapter to the PDF
def add_chapter(title, content):
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(200, 10, txt=title, ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=content)
    pdf.ln()

# Function to calculate financial ratios
def calculate_ratios(data):
    ratios = {}
    ratios['Inventory_Turnover_Ratio'] = float(data['CostOfRevenue']) / float(data['Inventory'])
    ratios['Days_Inventory_Outstanding'] = 365 / ratios['Inventory_Turnover_Ratio']
    ratios['Current_Ratio'] = float(data['CurrentAssets']) / float(data['CurrentLiabilities'])
    ratios['Quick_Ratio'] = (float(data['CurrentAssets']) - float(data['Inventory']) )/ float(data['CurrentLiabilities'])
    ratios['Debt_to_Equity_Ratio'] = float(data['TotalDebt']) / float(data['StockholdersEquity'])
    return ratios
    # Add more ratios as needed
    return ratios

def tonum(x):
    return denumerize.denumerize(x)
    
# Iterate over years
for year in years:

    # Prepare data for the year
    year_data = df[year]#.astype(float)
    year_data.index.name = None  # Remove index name for better presentation

    # Calculate COGS
    year_data['COGS'] = float(year_data['AccountsPayable']) + float(year_data['AccountsReceivable'])

    # Calculate financial ratios
    ratios = calculate_ratios(year_data)

    # Generate chapter content
    chapter_title = f"Financial Report for Year {year}"
    chapter_content = f"Inventory Turnover Ratio: {ratios['Inventory_Turnover_Ratio']:.2f}\n"
    chapter_content += f"Days Inventory Outstanding: {ratios['Days_Inventory_Outstanding']:.2f}\n"
    # Add more ratios as needed

    # Add chapter to PDF
    add_chapter(chapter_title, chapter_content)

# Add Executive Summary
add_chapter("Executive Summary", "The company's financial performance has been stable over the past three years.")

# Add Future Trend Prediction
add_chapter("Future Trend Prediction", "Based on the stable performance, it is predicted that the company will continue its current trend in the following year.")

# Save PDF
pdf_file_path = 'financial_report.pdf'
pdf.output(pdf_file_path)
print("Financial report saved as:", pdf_file_path)