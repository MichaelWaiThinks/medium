
# =============================================================================
# 
# from yahooquery import Screener
# 
# # Initialize the Yahoo Finance Screener
# s = Screener()
# 
# # Retrieve and print all available screeners to identify a valid one
# available_screeners = s.available_screeners
# print("Available Screeners:", available_screeners)
# xxxyyyzzz
# 
# # Choose a valid screener name
# # Here, we'll use 'most_actives' which is a common one
# screener_name = 'most_actives'
# screener_name = 'apparel_retail'
# screener_name = 'apparel_retail'
# screener_name ='department_stores'
# screener_name ='discount_stores'
# screener_name ='grocery_stores'
# 
# # Get sectors and industries using the chosen screener
# screen = s.get_screeners(screener_name, count=99)
# 
# print (screen)
# # Extract sectors and industries from the screener result
# sectors_industries = screen['finance']['result'][0]['tags']
# 
# # Display sectors and industries
# print("\nAvailable Sectors and Industries on Yahoo Finance:")
# for sector, industries in sectors_industries.items():
#     print(f"\nSector: {sector}")
#     for industry in industries:
#         print(f"  - Industry: {industry}")
# xxxyyyzzz
# =============================================================================

cnames = {
    'aliceblue':            '#F0F8FF',
    'antiquewhite':         '#FAEBD7',
    'aqua':                 '#00FFFF',
    'aquamarine':           '#7FFFD4',
    'azure':                '#F0FFFF',
    'beige':                '#F5F5DC',
    'bisque':               '#FFE4C4',
    'black':                '#000000',
    'blanchedalmond':       '#FFEBCD',
    'blue':                 '#0000FF',
    'blueviolet':           '#8A2BE2',
    'brown':                '#A52A2A',
    'burlywood':            '#DEB887',
    'cadetblue':            '#5F9EA0',
    'chartreuse':           '#7FFF00',
    'chocolate':            '#D2691E',
    'coral':                '#FF7F50',
    'cornflowerblue':       '#6495ED',
    'cornsilk':             '#FFF8DC',
    'crimson':              '#DC143C',
    'cyan':                 '#00FFFF',
    'darkblue':             '#00008B',
    'darkcyan':             '#008B8B',
    'darkgoldenrod':        '#B8860B',
    'darkgray':             '#A9A9A9',
    'darkgreen':            '#006400',
    'darkkhaki':            '#BDB76B',
    'darkmagenta':          '#8B008B',
    'darkolivegreen':       '#556B2F',
    'darkorange':           '#FF8C00',
    'darkorchid':           '#9932CC',
    'darkred':              '#8B0000',
    'darksalmon':           '#E9967A',
    'darkseagreen':         '#8FBC8F',
    'darkslateblue':        '#483D8B',
    'darkslategray':        '#2F4F4F',
    'darkturquoise':        '#00CED1',
    'darkviolet':           '#9400D3',
    'deeppink':             '#FF1493',
    'deepskyblue':          '#00BFFF',
    'dimgray':              '#696969',
    'dodgerblue':           '#1E90FF',
    'firebrick':            '#B22222',
    'floralwhite':          '#FFFAF0',
    'forestgreen':          '#228B22',
    'fuchsia':              '#FF00FF',
    'gainsboro':            '#DCDCDC',
    'ghostwhite':           '#F8F8FF',
    'gold':                 '#FFD700',
    'goldenrod':            '#DAA520',
    'gray':                 '#808080',
    'green':                '#008000',
    'greenyellow':          '#ADFF2F',
    'honeydew':             '#F0FFF0',
    'hotpink':              '#FF69B4',
    'indianred':            '#CD5C5C',
    'indigo':               '#4B0082',
    'ivory':                '#FFFFF0',
    'khaki':                '#F0E68C',
    'lavender':             '#E6E6FA',
    'lavenderblush':        '#FFF0F5',
    'lawngreen':            '#7CFC00',
    'lemonchiffon':         '#FFFACD',
    'lightblue':            '#ADD8E6',
    'lightcoral':           '#F08080',
    'lightcyan':            '#E0FFFF',
    'lightgoldenrodyellow': '#FAFAD2',
    'lightgreen':           '#90EE90',
    'lightgray':            '#D3D3D3',
    'lightpink':            '#FFB6C1',
    'lightsalmon':          '#FFA07A',
    'lightseagreen':        '#20B2AA',
    'lightskyblue':         '#87CEFA',
    'lightslategray':       '#778899',
    'lightsteelblue':       '#B0C4DE',
    'lightyellow':          '#FFFFE0',
    'lime':                 '#00FF00',
    'limegreen':            '#32CD32',
    'linen':                '#FAF0E6',
    'magenta':              '#FF00FF',
    'maroon':               '#800000',
    'mediumaquamarine':     '#66CDAA',
    'mediumblue':           '#0000CD',
    'mediumorchid':         '#BA55D3',
    'mediumpurple':         '#9370DB',
    'mediumseagreen':       '#3CB371',
    'mediumslateblue':      '#7B68EE',
    'mediumspringgreen':    '#00FA9A',
    'mediumturquoise':      '#48D1CC',
    'mediumvioletred':      '#C71585',
    'midnightblue':         '#191970',
    'mintcream':            '#F5FFFA',
    'mistyrose':            '#FFE4E1',
    'moccasin':             '#FFE4B5',
    'navajowhite':          '#FFDEAD',
    'navy':                 '#000080',
    'oldlace':              '#FDF5E6',
    'olive':                '#808000',
    'olivedrab':            '#6B8E23',
    'orange':               '#FFA500',
    'orangered':            '#FF4500',
    'orchid':               '#DA70D6',
    'palegoldenrod':        '#EEE8AA',
    'palegreen':            '#98FB98',
    'paleturquoise':        '#AFEEEE',
    'palevioletred':        '#DB7093',
    'papayawhip':           '#FFEFD5',
    'peachpuff':            '#FFDAB9',
    'peru':                 '#CD853F',
    'pink':                 '#FFC0CB',
    'plum':                 '#DDA0DD',
    'powderblue':           '#B0E0E6',
    'purple':               '#800080',
    'red':                  '#FF0000',
    'rosybrown':            '#BC8F8F',
    'royalblue':            '#4169E1',
    'saddlebrown':          '#8B4513',
    'salmon':               '#FA8072',
    'sandybrown':           '#FAA460',
    'seagreen':             '#2E8B57',
    'seashell':             '#FFF5EE',
    'sienna':               '#A0522D',
    'silver':               '#C0C0C0',
    'skyblue':              '#87CEEB',
    'slateblue':            '#6A5ACD',
    'slategray':            '#708090',
    'snow':                 '#FFFAFA',
    'springgreen':          '#00FF7F',
    'steelblue':            '#4682B4',
    'tan':                  '#D2B48C',
    'teal':                 '#008080',
    'thistle':              '#D8BFD8',
    'tomato':               '#FF6347',
    'turquoise':            '#40E0D0',
    'violet':               '#EE82EE',
    'wheat':                '#F5DEB3',
    'white':                '#FFFFFF',
    'whitesmoke':           '#F5F5F5',
    'yellow':               '#FFFF00',
    'yellowgreen':          '#9ACD32'

}
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from yahooquery import Screener

# Function to fetch stock symbols from the 'apparel_retail' industry
def fetch_stock_symbols(industry):
    s = Screener()
    screener_results = s.get_screeners(industry, count=50)  # Adjust count as needed

    # print(screener_results)
    
    # if 'finance' in screener_results and 'result' in screener_results['finance']:
    # symbols = screener_results['finance']['result'][0]['quotes']
    symbols = screener_results[industry]['quotes']
    stock_symbols = [stock['symbol'] for stock in symbols]
    # print(stock_symbols)
    
    return stock_symbols
    # else:
    #     print(f"No data found for industry: {industry}")
    #     return []

# Function to calculate the inventory turnover ratio for a given stock symbol
def calculate_turnover_ratio(symbol):
    try:
        company = yf.Ticker(symbol)

        # Get historical financial data (last 5 years)
        income_statement = company.financials.T
        balance_sheet = company.balance_sheet.T

        if 'Total Revenue' not in income_statement.columns or 'Cost Of Revenue' not in income_statement.columns or 'Inventory' not in balance_sheet.columns:
            return None

        # Create DataFrame for financials
        financials_df = pd.DataFrame({
            'Revenue': income_statement['Total Revenue'],
            'COGS': income_statement['Cost Of Revenue'],
            'Inventory': balance_sheet['Inventory'],
        })

        # Calculate Average Inventory and Inventory Turnover Ratio
        financials_df['Average Inventory'] = financials_df['Inventory'].rolling(window=2).mean()
        financials_df['Turnover Ratio'] = financials_df['COGS'] / financials_df['Average Inventory']
        
        # Add date index and reset to 'date' column
        financials_df['Date'] = financials_df.index
        financials_df['Company'] = symbol

        return financials_df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def main():
    industries = ['most_actives',
    'apparel_retail',
    'department_stores',
    'discount_stores',
    'grocery_stores',
    'specialty_retail']
    # s = pd.DataFrame()
    stock_symbols=[]
    for industry in industries:
        print(f'fetching symbols from {industry}')
        s = fetch_stock_symbols(industry)
        print(s)
        stock_symbols += s
    print(stock_symbols)
    if len( stock_symbols)<1:
        print("No stock symbols found.")
        return
    

    # Initialize an empty list to store data
    all_data = []

    # Fetch and calculate data for each stock symbol
    for i, symbol in enumerate(stock_symbols):
        print(f"Processing {symbol}...")
        df = calculate_turnover_ratio(symbol)
        if df is not None:
            all_data.append(df)
            plt.plot(df['Date'], df['Turnover Ratio'], alpha = 0.5,color='skyblue')#list(cnames)[i],label=symbol +' ' + str(round(df['Turnover Ratio'].mean(),1)) )
            # if symbol == 'ULTA':
            #     plt.annotate(xy=(df['Date'].iloc[0],df['Turnover Ratio'].iloc[3]), xytext=(5,0), textcoords='offset points', text=symbol, va='center')
            #     print(symbol,df['Date'].iloc[0],df['Turnover Ratio'])

    if all_data:
        # Combine all company data into a single DataFrame
        final_df = pd.concat(all_data).sort_values(by='Date')

        # Save to a CSV file
        final_df.to_csv(f'{industry}_inventory_turnover_data.csv', index=False)

        # Customize and show plot
        plt.title(f'Inventory Turnover Ratio for {industry} Companies (Last 5 Years)')
        plt.ylabel('Turnover Ratio')
        plt.xlabel('Date')
        plt.legend(loc='best', fontsize=10,bbox_to_anchor=(1.2, 1))
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(f'{industry}_inventory_turnover.png')

        # Display plot
        plt.show()
        
    else:
        print("No data available for the specified industry.")

if __name__ == '__main__':
    main()
