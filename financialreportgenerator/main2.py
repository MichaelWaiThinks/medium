#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 24 02:08:14 2024

@author: michaelwai
"""


from numerize_denumerize import numerize, denumerize
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF

# Read financial data from CSV
df = pd.read_csv('WMT_balance_sheet.csv',index_col=0)
print (df,df.columns)
for idx in df.index:
    print (df.loc[idx])
    try:
        df.loc[idx] = pd.to_numeric(df.loc[idx])
    except Exception as e:
        print (idx, str(e))
# =============================================================================
# # Extract years
# years = df.columns[1:].tolist()
#
# # Initialize DataFrame for ratios
# ratios_df = pd.DataFrame(index=df['asOfDate'])
#
# =============================================================================
print ('[[[',df,']]]')

# Generate the report
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Financial Ratios Report', align='C', ln=True)
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()


# Function to calculate financial ratios

# Calculate ratios
def calculate_ratios(df):
    print ('**** '),df
    ratios = {}

    # Liquidity Ratios
    ratios['Current Ratio'] = df.loc['CurrentAssets'] / df.loc['CurrentLiabilities']
    ratios['Quick Ratio'] = (df.loc['CurrentAssets'] - df.loc['Inventory']) / df.loc['CurrentLiabilities']

    # Solvency Ratios
    ratios['Debt to Equity Ratio'] = df.loc['TotalLiabilitiesNetMinorityInterest'] / df.loc['StockholdersEquity']
    ratios['Debt Ratio'] = df.loc['TotalLiabilitiesNetMinorityInterest'] / df.loc['TotalAssets']

    # Profitability Ratios
    ratios['GrossProfit Margin'] = (df.loc['GrossProfit'] / df.loc['TotalRevenue']) * 100
    ratios['Net Profit Margin'] = (df.loc['NetIncome'] / df.loc['TotalRevenue']) * 100
    ratios['Return on Assets (ROA)'] = (df.loc['NetIncome'] / df.loc['TotalAssets']) * 100
    ratios['Return on Equity (ROE)'] = (df.loc['NetIncome'] / df.loc['StockholdersEquity']) * 100

    # Activity Ratios
    ratios['AccountsReceivableTurnover'] = df.loc['TotalRevenue'] / df.loc['AccountsReceivable']
    ratios['Inventory Turnover'] = df.loc['CostOfRevenue'] / df.loc['Inventory']
    ratios['Days Sales in Inventory (DSI)'] = 365 / ratios['Inventory Turnover']
    ratios['Days Sales Outstanding (DSO)'] = 365 / ratios['AccountsReceivableTurnover']
    ratios['Accounts Payable Turnover'] = df.loc['AccountsReceivable'] / df.loc['AccountsPayable']
    ratios['Days Payable Outstanding (DPO)'] = 365 / ratios['Accounts Payable Turnover']
    ratios['Days Inventory Outstanding (DIO)'] = 365 / (df.loc['TotalRevenue'] / ((df.loc['Inventory'] + df.loc['Inventory']) / 2))
    ratios['Cash Conversion Cycle (CCC)'] = ratios['Days Sales Outstanding (DSO)'] + ratios['Days Inventory Outstanding (DIO)'] - ratios['Days Payable Outstanding (DPO)']

    # Leverage Ratios
    ratios['Interest Coverage Ratio'] = df.loc['EBIT'] / df.loc['InterestExpense']
    ratios['Debt Service Coverage Ratio'] = (df.loc['NetIncome'] + df.loc['InterestExpense'] + df.loc['ReconciledDepreciation']) / df.loc['TotalDebt']

    # Market Ratios
    ratios['Price to Earnings (P/E) Ratio'] = df.loc['Market Price per Share'] / df.loc['RetainedEarnings']
    ratios['Price to Book (P/B) Ratio'] = df.loc['Market Price per Share'] / df.loc['TangibleBookValue']

    # Additional requested ratios
    ratios['Working Capital Turnover'] = df.loc['Sales'] / (df.loc['Current Assets'] - df.loc['Current Liabilities'])
    ratios['Fixed Charge Coverage Ratio'] = (df.loc['EBIT'] + df.loc['Lease Payments']) / (df.loc['Interest Expense'] + df.loc['Lease Payments'])
    ratios['Debt Service Coverage Ratio'] = (df.loc['EBIT'] + df.loc['Lease Payments']) / (df.loc['Interest Expense'] + df.loc['Lease Payments'] + df.loc['Principal Payments'])
    ratios['Cash Flow to Debt Ratio'] = df.loc['Operating Cash Flow'] / df.loc['Total Debt']
    ratios['Operating Cash Flow to Current Liabilities'] = df.loc['Operating Cash Flow'] / df.loc['Current Liabilities']
    ratios['Cash Flow Margin'] = (df.loc['Operating Cash Flow'] / df.loc['TotalRevenue']) * 100
    ratios['Cash Return on Assets (CROA)'] = df.loc['Operating Cash Flow'] / df.loc['TotalAssets']
    ratios['Cash Return on Equity (CROE)'] = df.loc['Operating Cash Flow'] / df.loc['StockholdersEquity']
    ratios['Cash Return on Invested Capital (CROIC)'] = df.loc['Operating Cash Flow'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'])
    ratios['Gross Operating Margin'] = (df.loc['Operating Income'] / df.loc['TotalRevenue']) * 100
    ratios['Return on Gross Assets (ROGA)'] = df.loc['NetIncome'] / df.loc['Gross PPE']
    ratios['Return on Gross Investment (ROGI)'] = df.loc['NetIncome'] / (df.loc['Gross PPE'] + df.loc['Construction In Progress'])
    ratios['Return on Total Investment (ROTI)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] + df.loc['Additional Paid in Capital'] - df.loc['Current Liabilities'])
    ratios['Return on Invested Assets (ROIA)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'])
    ratios['Return on Capital (ROC)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] + df.loc['Current Liabilities'] + df.loc['Long-term Liabilities'])
    ratios['Return on Capital Employed (ROCE)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] + df.loc['Current Liabilities'] + df.loc['Long-term Liabilities'] - df.loc['Current Liabilities'] + df.loc['Current Liabilities'] + df.loc['Long-term Liabilities'] - df.loc['Short-term Investments'] + df.loc['Additional Paid in Capital'] + df.loc['Retained Earnings'])
    ratios['Return on Average Capital Employed (ROACE)'] = df.loc['NetIncome'] / (((df.loc['TotalAssets'] - df.loc['Current Liabilities']) + (df.loc['TotalAssets'] - df.loc['Current Liabilities']) + (df.loc['TotalAssets'] - df.loc['Current Liabilities']) + (df.loc['TotalAssets'] - df.loc['Current Liabilities'])) / 4)
    ratios['Return on Operating Capital (ROOC)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'])
    ratios['Return on Operating Liabilities (ROOL)'] = df.loc['NetIncome'] / (df.loc['Total Liabilities'] - df.loc['Current Liabilities'])
    ratios['Return on Operating Capital Employed (ROOCE)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] + df.loc['Current Liabilities'] + df.loc['Long-term Liabilities'])
    ratios['Return on Long-term Assets (ROLA)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Assets'] - df.loc['Current Liabilities'])
    ratios['Return on Long-term Capital (ROLT)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] + df.loc['Long-term Debt'] - df.loc['Cash'])
    ratios['Return on Long-term Equity (ROLE)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] + df.loc['Long-term Debt'] - df.loc['Cash'] + df.loc['Current Liabilities'])
    ratios['Return on Total Capital (ROTC)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] + df.loc['Long-term Debt'] - df.loc['Cash'] + df.loc['Current Liabilities'] + df.loc['Current Liabilities'] + df.loc['Long-term Liabilities'])
    ratios['Return on Total Invested Capital (ROTIC)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] + df.loc['Long-term Debt'] - df.loc['Cash'] + df.loc['Current Liabilities'] + df.loc['Current Liabilities'] + df.loc['Long-term Liabilities'] + df.loc['Current Liabilities'] + df.loc['Long-term Liabilities'] - df.loc['Short-term Investments'])
    ratios['Return on Total Operating Assets (ROTOA)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Assets'] - df.loc['Current Liabilities'] - df.loc['Long-term Liabilities'] - df.loc['Short-term Investments'])
    ratios['Return on Total Operating Capital (ROTOC)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Long-term Liabilities'] - df.loc['Short-term Investments'])
    ratios['Return on Total Operating Equity (ROTOE)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] - df.loc['Short-term Investments'])
    ratios['Return on Total Operating Investment (ROTOI)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Long-term Liabilities'] - df.loc['Short-term Investments'])
    ratios['Return on Tangible Capital (ROTC)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] + df.loc['Long-term Debt'] - df.loc['Cash'] - df.loc['Goodwill'] - df.loc['Intangible Assets'])
    ratios['Return on Tangible Equity (ROTE)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] + df.loc['Long-term Debt'] - df.loc['Cash'] - df.loc['Goodwill'] - df.loc['Intangible Assets'] + df.loc['Current Liabilities'])
    ratios['Return on Tangible Assets (ROTA)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Assets'] - df.loc['Current Liabilities'] - df.loc['Intangible Assets'])
    ratios['Return on Tangible Invested Capital (ROTIC)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] + df.loc['Long-term Debt'] - df.loc['Cash'] - df.loc['Goodwill'] - df.loc['Intangible Assets'] + df.loc['Current Liabilities'] + df.loc['Long-term Liabilities'])
    ratios['Return on Tangible Operating Assets (ROTOA)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Assets'] - df.loc['Current Liabilities'] - df.loc['Long-term Liabilities'] - df.loc['Short-term Investments'] - df.loc['Intangible Assets'])
    ratios['Return on Tangible Operating Capital (ROTOC)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Long-term Liabilities'] - df.loc['Short-term Investments'] - df.loc['Intangible Assets'])
    ratios['Return on Tangible Operating Equity (ROTOE)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] - df.loc['Short-term Investments'] - df.loc['Intangible Assets'])
    ratios['Return on Tangible Operating Investment (ROTOI)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Long-term Liabilities'] - df.loc['Short-term Investments'] - df.loc['Intangible Assets'])
    ratios['Return on Invested Capital (ROIC)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'] - df.loc['Long-term Debt'])
    ratios['Return on Incremental Capital (ROIC)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'] - df.loc['Long-term Debt'])
    ratios['Return on Incremental Invested Capital (ROIIC)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'] - df.loc['Long-term Debt'])
    ratios['Return on Incremental Operating Capital (ROIOC)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'] - df.loc['Long-term Debt'])
    ratios['Return on Incremental Operating Equity (ROIOE)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'] - df.loc['Long-term Debt'] + df.loc['Current Liabilities'])
    ratios['Return on Incremental Operating Investment (ROIOI)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'] - df.loc['Long-term Debt'])
    ratios['Return on Invested Equity (ROIE)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] - df.loc['Short-term Investments'])
    ratios['Return on Invested Investment (ROII)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'])
    ratios['Return on Operating Investment (ROOI)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'] - df.loc['Long-term Liabilities'])
    ratios['Return on Operating Equity (ROOE)'] = df.loc['NetIncome'] / (df.loc['StockholdersEquity'] - df.loc['Short-term Investments'])
    ratios['Return on Operating Assets (ROOA)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Assets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'] - df.loc['Long-term Liabilities'])
    ratios['Return on Operating Invested Capital (ROOIC)'] = df.loc['NetIncome'] / (df.loc['TotalAssets'] - df.loc['Current Liabilities'] - df.loc['Short-term Investments'] - df.loc['Long-term Liabilities'] - df.loc['Intangible Assets'])

    return descriptions.get(ratio, 'No description available.')

ratios = calculate_ratios(df)
# =============================================================================
#
# # Iterate over rows and calculate ratios
# for index, row in df.iterrows():
#     data = row[1:].astype(float)
#     print ('=>',data,index,row)
#     ratios = calculate_ratios(data)
#     for ratio, value in ratios.items():
#         ratios_df.loc[row['Year'], ratio] = value
#
# =============================================================================
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

# Function to interpret and analyze each row
def analyze_row(row):
    insight = f"Analysis of {row['Year']}:\n"
    insight += f"- Current Ratio: {row['Current_Ratio']:.2f}\n"
    insight += f"- Quick Ratio: {row['Quick_Ratio']:.2f}\n"
    insight += f"- Debt to Equity Ratio: {row['Debt_to_Equity_Ratio']:.2f}\n"
    # Add more ratios as needed

    # Interpret past performance and future outlook
    performance_insight = "Past Performance:\n"
    future_outlook_insight = "Future Outlook:\n"
    # Add interpretation logic here

    return insight, performance_insight, future_outlook_insight

# Iterate over rows and generate report
for index, row in ratios_df.iterrows():
    insight, performance_insight, future_outlook_insight = analyze_row(row)
    report_content = insight + "\n" + performance_insight + "\n" + future_outlook_insight + "\n"
    chapter_title = f"Financial Report for {index}"
    add_chapter(chapter_title, report_content)


# Save PDF
pdf_file_path = 'financial_ratios_report.pdf'
pdf.output(pdf_file_path)
print("Financial ratios report saved as:", pdf_file_path)
