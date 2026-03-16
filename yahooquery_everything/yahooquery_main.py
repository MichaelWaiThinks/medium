#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 13 17:47:56 2024

@author: michaelwai
"""

from yahooquery import Ticker,Screener # pip install yahooquery
import pandas as pd
import traceback
from os.path import expanduser
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as patches

from matplotlib.dates import DateFormatter
from matplotlib.ticker import FuncFormatter

import numpy as np
import math
# import yfinance as yf

import datetime as dt
today_str=dt.datetime.today().strftime('%Y-%m-%d')
# https://yahooquery.dpguthrie.com/guide/ticker/financials/#all_financial_data

# =============================================================================
# print (df.index)
# for module in df.index:
#     print ('\'',module,'\'')
# =============================================================================

symbol='MSFT'
complete_df=[] #list of pandas

#dfindex is actually below
querymodule_list=[
    'assetProfile',
    'balanceSheetHistory',
    'balanceSheetHistoryQuarterly',
    'calendarEvents',
    'cashflowStatementHistory',
    'cashflowStatementHistoryQuarterly',
    'defaultKeyStatistics',
    'earnings',
    'earningsHistory',
    'earningsTrend',
    'esgScores',
    'financialData',
    'fundOwnership',
    'incomeStatementHistory',
    'incomeStatementHistoryQuarterly',
    'indexTrend',
    'industryTrend',
    'insiderHolders',
    'insiderTransactions',
    'institutionOwnership',
    'majorHoldersBreakdown',
    'netSharePurchaseActivity',
    'pageViews',
    'price',
    'quoteType',
    'recommendationTrend',
    'secFilings', ##
    'sectorTrend',
    'summaryDetail',
    'summaryProfile',
    'upgradeDowngradeHistory'
]

methods=[
    'all_financial_data',
    'cash_flow',
    'balance_sheet',
    'income_statement',
    'valuation_measures',
    'option_chain',
    'corporate_events',
    'news',
    'quotes',
    'recommendations',
    'technical_insights'

    ]

screener=[
   'advertising_agencies',
  'aerospace_defense',
  'aggressive_small_caps',
  'agricultural_inputs',
  'airlines',
  'airports_air_services',
  'all_cryptocurrencies_au',
  'all_cryptocurrencies_ca',
  'all_cryptocurrencies_eu',
  'all_cryptocurrencies_gb',
  'all_cryptocurrencies_in',
  'all_cryptocurrencies_us',
  'aluminum',
  'analyst_strong_buy_stocks',
  'apparel_manufacturing',
  'apparel_retail',
  'asset_management',
  'auto_manufacturers',
  'auto_parts',
  'auto_truck_dealerships',
  'banks_diversified',
  'banks_regional',
  'bearish_stocks_right_now',
  'best_hist_performance_etfs',
  'best_hist_performance_etfs_asia',
  'best_hist_performance_etfs_europe',
  'best_hist_performance_mutual_funds',
  'best_hist_performance_mutual_funds_asia',
  'best_hist_performance_mutual_funds_europe',
  'beverages_brewers',
  'beverages_non_alcoholic',
  'beverages_wineries_distilleries',
  'biotechnology',
  'bond_etfs',
  'bond_mutual_funds',
  'bond_mutual_funds_asia',
  'bond_mutual_funds_europe',
  'broadcasting',
  'building_materials',
  'building_products_equipment',
  'bullish_stocks_right_now',
  'business_equipment_supplies',
  'capital_markets',
  'cheapest_etfs',
  'cheapest_etfs_asia',
  'cheapest_etfs_europe',
  'cheapest_mutual_funds',
  'cheapest_mutual_funds_asia',
  'cheapest_mutual_funds_europe',
  'chemicals',
  'coking_coal',
  'commodity_etfs',
  'commodity_etfs_asia',
  'commodity_etfs_europe',
  'commodity_mutual_funds',
  'communication_equipment',
  'community_sentiment_most_bearish',
  'community_sentiment_most_bullish',
  'computer_hardware',
  'confectioners',
  'conglomerates',
  'conservative_foreign_funds',
  'consulting_services',
  'consumer_electronics',
  'copper',
  'credit_services',
  'day_gainers',
  'day_gainers_americas',
  'day_gainers_asia',
  'day_gainers_au',
  'day_gainers_br',
  'day_gainers_ca',
  'day_gainers_cryptocurrencies',
  'day_gainers_de',
  'day_gainers_dji',
  'day_gainers_es',
  'day_gainers_etfs',
  'day_gainers_etfs_asia',
  'day_gainers_etfs_europe',
  'day_gainers_europe',
  'day_gainers_fr',
  'day_gainers_gb',
  'day_gainers_hk',
  'day_gainers_in',
  'day_gainers_it',
  'day_gainers_mutual_funds',
  'day_gainers_mutual_funds_asia',
  'day_gainers_mutual_funds_europe',
  'day_gainers_ndx',
  'day_gainers_nz',
  'day_gainers_options',
  'day_gainers_sg',
  'day_losers',
  'day_losers_americas',
  'day_losers_asia',
  'day_losers_au',
  'day_losers_br',
  'day_losers_ca',
  'day_losers_cryptocurrencies',
  'day_losers_de',
  'day_losers_dji',
  'day_losers_es',
  'day_losers_etfs',
  'day_losers_etfs_asia',
  'day_losers_etfs_europe',
  'day_losers_europe',
  'day_losers_fr',
  'day_losers_gb',
  'day_losers_hk',
  'day_losers_in',
  'day_losers_it',
  'day_losers_mutual_funds',
  'day_losers_mutual_funds_asia',
  'day_losers_mutual_funds_europe',
  'day_losers_ndx',
  'day_losers_nz',
  'day_losers_options',
  'day_losers_sg',
  'department_stores',
  'diagnostics_research',
  'discount_stores',
  'drug_manufacturers_general',
  'drug_manufacturers_specialty_generic',
  'education_training_services',
  'electrical_equipment_parts',
  'electronic_components',
  'electronic_gaming_multimedia',
  'electronics_computer_distribution',
  'engineering_construction',
  'entertainment',
  'equity_mutual_funds',
  'farm_heavy_construction_machinery',
  'farm_products',
  'fifty_two_wk_gainers',
  'fifty_two_wk_gainers_asia',
  'fifty_two_wk_gainers_cryptocurrencies',
  'fifty_two_wk_gainers_etfs',
  'fifty_two_wk_gainers_etfs_asia',
  'fifty_two_wk_gainers_etfs_europe',
  'fifty_two_wk_gainers_europe',
  'fifty_two_wk_gainers_mutual_funds',
  'fifty_two_wk_gainers_mutual_funds_asia',
  'fifty_two_wk_gainers_mutual_funds_europe',
  'fifty_two_wk_losers',
  'fifty_two_wk_losers_asia',
  'fifty_two_wk_losers_cryptocurrencies',
  'fifty_two_wk_losers_etfs',
  'fifty_two_wk_losers_etfs_asia',
  'fifty_two_wk_losers_etfs_europe',
  'fifty_two_wk_losers_europe',
  'fifty_two_wk_losers_mutual_funds',
  'fifty_two_wk_losers_mutual_funds_asia',
  'fifty_two_wk_losers_mutual_funds_europe',
  'financial_conglomerates',
  'financial_data_stock_exchanges',
  'food_distribution',
  'footwear_accessories',
  'furnishings_fixtures_appliances',
  'gambling',
  'gold',
  'grocery_stores',
  'growth_technology_stocks',
  'health_information_services',
  'healthcare_plans',
  'high_growth_large_etfs',
  'high_growth_large_mutual_funds',
  'high_yield_bond',
  'high_yield_high_return',
  'high_yield_high_return_asia',
  'high_yield_high_return_europe',
  'home_improvement_retail',
  'household_personal_products',
  'industrial_distribution',
  'information_technology_services',
  'infrastructure_operations',
  'insurance_brokers',
  'insurance_diversified',
  'insurance_life',
  'insurance_property_casualty',
  'insurance_reinsurance',
  'insurance_specialty',
  'integrated_freight_logistics',
  'internet_content_information',
  'internet_retail',
  'large_blend_etfs',
  'large_blend_mutual_funds',
  'largest_market_cap',
  'largest_market_cap_asia',
  'largest_market_cap_cryptocurrencies',
  'largest_market_cap_europe',
  'latest_analyst_upgraded_stocks',
  'leisure',
  'lodging',
  'low_risk_mutual_funds',
  'low_risk_mutual_funds_asia',
  'low_risk_mutual_funds_europe',
  'lumber_wood_production',
  'luxury_goods',
  'marine_shipping',
  'medical_care_facilities',
  'medical_devices',
  'medical_distribution',
  'medical_instruments_supplies',
  'mega_cap_hc',
  'metal_fabrication',
  'morningstar_five_star_stocks',
  'mortgage_finance',
  'most_actives',
  'most_actives_americas',
  'most_actives_asia',
  'most_actives_au',
  'most_actives_br',
  'most_actives_ca',
  'most_actives_cn',
  'most_actives_cryptocurrencies',
  'most_actives_de',
  'most_actives_dji',
  'most_actives_es',
  'most_actives_etfs',
  'most_actives_etfs_asia',
  'most_actives_etfs_europe',
  'most_actives_europe',
  'most_actives_fr',
  'most_actives_gb',
  'most_actives_hk',
  'most_actives_in',
  'most_actives_it',
  'most_actives_ndx',
  'most_actives_nz',
  'most_actives_options',
  'most_actives_sg',
  'most_institutionally_bought_large_cap_stocks',
  'most_institutionally_held_large_cap_stocks',
  'most_institutionally_sold_large_cap_stocks',
  'most_shorted_stocks',
  'most_visited',
  'most_visited_basic_materials',
  'most_visited_communication_services',
  'most_visited_consumer_cyclical',
  'most_visited_consumer_defensive',
  'most_visited_energy',
  'most_visited_financial_services',
  'most_visited_healthcare',
  'most_visited_industrials',
  'most_visited_real_estate',
  'most_visited_technology',
  'most_visited_utilities',
  'most_watched_tickers',
  'ms_basic_materials',
  'ms_communication_services',
  'ms_consumer_cyclical',
  'ms_consumer_defensive',
  'ms_energy',
  'ms_financial_services',
  'ms_healthcare',
  'ms_industrials',
  'ms_real_estate',
  'ms_technology',
  'ms_utilities',
  'net_net_strategy',
  'net_net_strategy_asia',
  'net_net_strategy_europe',
  'oil_gas_drilling',
  'oil_gas_e_p',
  'oil_gas_equipment_services',
  'oil_gas_integrated',
  'oil_gas_midstream',
  'oil_gas_refining_marketing',
  'other_industrial_metals_mining',
  'other_precious_metals_mining',
  'packaged_foods',
  'packaging_containers',
  'paper_paper_products',
  'personal_services',
  'pharmaceutical_retailers',
  'pollution_treatment_controls',
  'portfolio_actions_most_added',
  'portfolio_actions_most_deleted',
  'portfolio_anchors',
  'precious_metal_etfs',
  'precious_metal_mutual_funds',
  'publishing',
  'railroads',
  'real_estate_development',
  'real_estate_diversified',
  'real_estate_services',
  'recreational_vehicles',
  'reit_diversified',
  'reit_healthcare_facilities',
  'reit_hotel_motel',
  'reit_industrial',
  'reit_mortgage',
  'reit_office',
  'reit_residential',
  'reit_retail',
  'reit_specialty',
  'rental_leasing_services',
  'residential_construction',
  'resorts_casinos',
  'restaurants',
  'scientific_technical_instruments',
  'security_protection_services',
  'semiconductor_equipment_materials',
  'semiconductors',
  'shell_companies',
  'silver',
  'small_cap_gainers',
  'software_application',
  'software_infrastructure',
  'solar',
  'solid_large_growth_funds',
  'solid_midcap_growth_funds',
  'sp_500_etfs',
  'sp_500_etfs_asia',
  'sp_500_etfs_europe',
  'specialty_business_services',
  'specialty_chemicals',
  'specialty_industrial_machinery',
  'specialty_retail',
  'staffing_employment_services',
  'steel',
  'stocks_most_bought_by_hedge_funds',
  'stocks_most_bought_by_pension_fund',
  'stocks_most_bought_by_private_equity',
  'stocks_most_bought_by_sovereign_wealth_fund',
  'stocks_with_most_institutional_buyers',
  'stocks_with_most_institutional_sellers',
  'strong_undervalued_stocks',
  'technology_etfs',
  'technology_mutual_funds',
  'telecom_services',
  'textile_manufacturing',
  'the_acquirers_multiple',
  'the_acquirers_multiple_asia',
  'the_acquirers_multiple_europe',
  'thermal_coal',
  'tobacco',
  'tools_accessories',
  'top_energy_us',
  'top_etfs',
  'top_etfs_hk',
  'top_etfs_in',
  'top_etfs_us',
  'top_mutual_funds',
  'top_mutual_funds_au',
  'top_mutual_funds_br',
  'top_mutual_funds_ca',
  'top_mutual_funds_de',
  'top_mutual_funds_es',
  'top_mutual_funds_fr',
  'top_mutual_funds_gb',
  'top_mutual_funds_hk',
  'top_mutual_funds_in',
  'top_mutual_funds_it',
  'top_mutual_funds_nz',
  'top_mutual_funds_sg',
  'top_mutual_funds_us',
  'top_options_implied_volatality',
  'top_options_open_interest',
  'top_performing_etfs',
  'top_performing_etfs_asia',
  'top_performing_etfs_europe',
  'top_performing_mutual_funds',
  'top_performing_mutual_funds_asia',
  'top_performing_mutual_funds_europe',
  'top_stocks_owned_by_cathie_wood',
  'top_stocks_owned_by_goldman_sachs',
  'top_stocks_owned_by_ray_dalio',
  'top_stocks_owned_by_warren_buffet',
  'travel_services',
  'trucking',
  'undervalued_growth_stocks',
  'undervalued_large_caps',
  'undervalued_wide_moat_stocks',
  'upside_breakout_stocks_daily',
  'uranium',
  'utilities_diversified',
  'utilities_independent_power_producers',
  'utilities_regulated_electric',
  'utilities_regulated_gas',
  'utilities_regulated_water',
  'utilities_renewable',
  'waste_management'
   ]

df_everything=pd.DataFrame()

def query_screener():
    s = Screener()

    # print (s.available_screeners)
    df=s.get_screeners(['most_actives'], 5)
    # print(df)

def query_module(ticker):
        ticker_data = ticker.all_modules

        df_data=pd.DataFrame.from_dict(ticker_data)
        df_data.to_csv(expanduser(dir_path+'/_'+symbol+'_rawdata.csv'))#,mode='a')

        df_index=df_data.index

        df_expanded=pd.DataFrame()

        idx=var_element='_'
        for idx in querymodule_list:
            SPLIT_INDICATOR=0

            # print (ticker.assetProfile)
            try:
                if idx in df_data.index:
                    df_module_dict=df_data.loc[idx][symbol]
                    # print(idx,df_module_dict)
                    flat_df=pd.json_normalize(df_module_dict, max_level=2)
                    df_element=pd.DataFrame.from_dict(flat_df).transpose()
                    df_element.reset_index()

                    for i in range(len(df_element)):
                        if type(df_element[0].iloc[i])==list:
                            dict_len=len(df_element[0].iloc[i])

                            if dict_len:
                                if type(df_element[0].iloc[i][0])==dict:
                                    for j in range(dict_len):
                                        try:
                                            var_element= (df_element[0].index[j])
                                            if  var_element =='balanceSheetStatements' or\
                                                var_element =='cashflowStatements' or\
                                                var_element =='earningsChart.quarterly' or\
                                                var_element =='financialsChart.yearly' or\
                                                var_element =='inancialsChart.quarterly' or\
                                                var_element =='history' or\
                                                var_element =='trend' or\
                                                var_element =='ownershipList' or\
                                                var_element =='incomeStatementHistory' or\
                                                var_element =='estimates' or\
                                                var_element =='holders' or\
                                                var_element =='transactions' or\
                                                var_element =='ownershipList' or\
                                                var_element =='filings' or\
                                                var_element =='transactions' :

                                                flat_df = pd.concat([pd.DataFrame(pd.json_normalize(x)) for x in df_element[0].loc[var_element]],ignore_index=True)
                                                flat_df.reset_index()
                                                flat_df.to_csv(expanduser(dir_path+'/'+symbol+'_'+idx+'_'+var_element+'.csv'))

                                                # df_element=pd.concat([df_element,flat_df])
                                                SPLIT_INDICATOR +=1
                                            else:
                                                flat_df=pd.json_normalize(df_element[0].iloc[i][j])
                                                flat_df=pd.DataFrame.from_dict(flat_df).transpose()
                                                flat_df=flat_df.add_prefix(str(df_element[0].index[i]+'_'), axis=0)
                                                df_element=pd.concat([df_element,flat_df])
                                        except Exception as e:
                                            print (j,'#',df_element, ' error: ',df_element[0].iloc[i][j], str(e))
                                            continue
                                    # df_element[0].iloc[i]='<TO BE REMOVED>' #(i) #replace whole row with nan

                    df_element.columns=[symbol.upper()]
                    if SPLIT_INDICATOR:
                        SPLIT_INDICATOR = '(split '+str(SPLIT_INDICATOR)+')'
                    else:
                        SPLIT_INDICATOR=''
                    df_element.to_csv(expanduser(dir_path+'/'+symbol+'_'+idx+SPLIT_INDICATOR+'.csv'))

                    print ('****** %s [%s] *****\n'% (idx,df_element.shape[0]))

                    df_expanded = pd.concat([df_expanded,df_element])
            except Exception as e:
                print ('Error when processing %s:%s:%s' %(idx,df_module_dict,var_element) , traceback.format_exc())
                continue

            # let's keep the expanded results
            # df_expanded = df_expanded[df_expanded[symbol]!='<TO BE REMOVED>']
            df_expanded.to_csv(expanduser(dir_path+'/_'+str(symbol)+'_'+'all_module_data.csv'))


        return df_expanded

def query_finance(ticker):

    yq_d = {}

    for method in methods:
        # df = getattr(ticker, method)()
        try:
            SPLIT_INDICATOR=0
            df=pd.DataFrame()

            if 'all_financial_data' in method:
                df=ticker.all_financial_data()
                if type(df)==str: continue
                SPLIT_INDICATOR += 1
                # df = df.T
            if 'cash_flow' in method:
                df=ticker.cash_flow()
                if type(df)==str: continue
                df.set_index(['asOfDate', 'periodType'], inplace=True)
                df = df.T
                SPLIT_INDICATOR += 1

            if 'balance_sheet' in method:
                df=ticker.balance_sheet()
                if type(df)==str: continue
                df.set_index(['asOfDate', 'periodType'], inplace=True)
                df = df.T
                SPLIT_INDICATOR += 1

            if 'income_statement' in method:
                df=ticker.income_statement()
                if type(df)==str: continue
                df.set_index(['asOfDate', 'periodType'], inplace=True)
                df = df.T
                SPLIT_INDICATOR += 1

            if 'valuation_measures' in method:
                df=ticker.valuation_measures
                if type(df)==str: continue
                df = df.T
                SPLIT_INDICATOR += 1

            if 'option_chain' in method:
                df=ticker.option_chain
                if type(df)==str: continue
                df = df.T
                SPLIT_INDICATOR += 1

            if 'corporate_events' in method:
                df=ticker.corporate_events
                if type(df)==str: continue
                df = df.T
                SPLIT_INDICATOR += 1

            if 'news' in method:
                df=pd.DataFrame([ticker.news(5)])
                if type(df)==str: continue
                df = df.T
                SPLIT_INDICATOR += 1

            if 'quotes' in method:
                df=pd.DataFrame.from_dict(ticker.quotes)
                if type(df)==str: continue
                # df = df.T
                SPLIT_INDICATOR += 1

            if 'recommendations' in method:
                df=pd.DataFrame.from_dict(ticker.recommendations)
                if type(df)==str: continue
                df = pd.concat([pd.DataFrame(pd.json_normalize(x)) for x in df.loc['recommendedSymbols']],ignore_index=True)
                df.reset_index()
                # df = df.T
                SPLIT_INDICATOR += 1

            if 'technical_insights' in method:
                df_result=pd.DataFrame()
                df=pd.DataFrame.from_dict(ticker.technical_insights)
                if type(df)==str: continue

                if 'companySnapshot' in df.index:

                    df_tmp = pd.concat([pd.DataFrame(pd.json_normalize(x)) for x in df.loc['companySnapshot']],ignore_index=True)
                    df_tmp.reset_index()
                    df_tmp.to_csv(expanduser(dir_path+'/'+symbol+'_'+method+'_companySnapshot'+'.csv'))
                    SPLIT_INDICATOR += 1

                if 'instrumentInfo' in df.index:

                    df_tmp = pd.concat([pd.DataFrame(pd.json_normalize(x)) for x in df.loc['instrumentInfo']],ignore_index=True)
                    df_tmp.reset_index()
                    df_tmp.to_csv(expanduser(dir_path+'/'+symbol+'_'+method+'_instrumentInfo'+'.csv'))
                    SPLIT_INDICATOR += 1

                if 'recommendation' in df.index:

                    df_tmp = pd.concat([pd.DataFrame(pd.json_normalize(x)) for x in df.loc['recommendation']],ignore_index=True)
                    df_tmp.reset_index()
                    df_tmp.to_csv(expanduser(dir_path+'/'+symbol+'_'+method+'_recommendation'+'.csv'))
                    SPLIT_INDICATOR += 1

                if 'secReports' in df.index:

                    df_tmp = pd.concat([pd.DataFrame(pd.json_normalize(x)) for x in df.loc['secReports']],ignore_index=True)
                    df_tmp.reset_index()
                    df_tmp.to_csv(expanduser(dir_path+'/'+symbol+'_'+method+'_secReports'+'.csv'))
                    SPLIT_INDICATOR += 1

                if 'sigDevs' in df.index:

                    df_tmp = pd.concat([pd.DataFrame(pd.json_normalize(x)) for x in df.loc['sigDevs']],ignore_index=True)
                    df_tmp.reset_index()
                    df_tmp.to_csv(expanduser(dir_path+'/'+symbol+'_'+method+'_sigDevs''.csv'))
                    SPLIT_INDICATOR += 1

            if type(df)!=str:
                print ('***** %s [%s] *****' % (method, df.shape[0]))
                if SPLIT_INDICATOR:
                    SPLIT_INDICATOR = '(split '+str(SPLIT_INDICATOR)+')'
                else:
                    SPLIT_INDICATOR=''

                df.to_csv(expanduser(dir_path+'/'+symbol+'_'+method+SPLIT_INDICATOR+'.csv'))
            else:
                print ('***** %s [%s] *****' % (method, df))
        except Exception as e:
            print ('***** %s [%s] *****' % (method, 'error'))

            print ('Error when processing %s' %(method) , traceback.format_exc())
            continue

    return True

def plot_chart(df,col,ax1,title=''):
    # chart beautification
    ax1.grid(True, color='silver',linewidth=0.5)
    ax1.set_ylabel(col+' '+title,fontsize=10)

    # plt.suptitle(f'Japan Nikken index 1998 - 2024',fontsize=10)
    # ax2.set_xticklabels(df['Date'],rotation=90,fontsize=6)
    date_form = DateFormatter("%m/%y")
    ax1.xaxis.set_major_formatter(date_form)
    ax1.grid(color='grey', linestyle='--', linewidth=0.2)
    ax1.yaxis.tick_right()
    ax1.xaxis.set_major_locator(plt.MaxNLocator(10))
    ax1.yaxis.set_major_locator(plt.MaxNLocator(5))

    # plotting normal stock price
    ax1.plot(df['Date'],df[col], color='darkblue',linewidth=0.5)
    # ax1.fill_between(df['Date'],df[col], 0,where=df[col] > 0,facecolor='green',  alpha=0.6,edgecolor=None,linewidth=0)
    # ax1.fill_between(df['Date'],df[col],0,where=df[col] < 0,facecolor='red',  alpha=0.6,edgecolor=None,linewidth=0)

    return fig

def thousands(x, pos):
    'The two args are the value and tick position'
    return '%1.0fK' % (x*1e-3)
def round_and_group(data,base=5):
    df = data[['strike', 'volume']].copy()
    #Round to nearest X
    df['strike'] = df['strike'].apply(lambda x: custom_round(x, base=base))
    # Remove the date index
    df = df.set_index('strike')
    df = df.groupby(['strike']).sum()

    return df
# {'NVDA': {'maxAge': 86400, 'currentPrice': 903.5979, 'targetHighPrice': 1279.36, 'targetLowPrice': 420.36, 'targetMeanPrice': 784.71, 'targetMedianPrice': 785.89, 'recommendationMean': 1.7, 'recommendationKey': 'buy', 'numberOfAnalystOpinions': 46, 'totalCash': 25984000000, 'totalCashPerShare': 10.394, 'ebitda': 34480001024, 'totalDebt': 11056000000, 'quickRatio': 3.385, 'currentRatio': 4.171, 'totalRevenue': 60921999360, 'debtToEquity': 25.725, 'revenuePerShare': 24.675, 'returnOnAssets': 0.38551, 'returnOnEquity': 0.91458, 'freeCashflow': 19866875904, 'operatingCashflow': 28089999360, 'earningsGrowth': 7.613, 'revenueGrowth': 2.653, 'grossMargins': 0.72718, 'ebitdaMargins': 0.56597, 'operatingMargins': 0.61592996, 'profitMargins': 0.48849, 'financialCurrency': 'USD'}}


def remove_outliner(df, columns, threshold=3): #sometimes we have data which is outliner from Yahoo we need to clean
    df_cleaned = df.copy()
    # Iterate over each column
    for col in columns:
        if col in df_cleaned.columns:
            print('cleaning ', col)
            # Calculate Z-score for each value in the column
            z_scores = np.abs(
                (df_cleaned[col] - df_cleaned[col].mean()) / df_cleaned[col].std())

            # Find indices of outliers based on Z-score exceeding threshold
            outlier_indices = z_scores > threshold

            # Replace outliers with NaNs
            df_cleaned.loc[outlier_indices , col] = np.nan

            # Drop rows containing NaNs
            df_cleaned = df_cleaned.dropna()

    return df_cleaned

def remove_duplicate_label(ax):
    handles, labels = ax.get_legend_handles_labels()
    unique = [(h, l) for i, (h, l) in enumerate(zip(handles, labels)) if l not in labels[:i]]
    ax.legend(*zip(*unique))

def show_option_chain():
    start_date='2020-01-01'
    df = pd.DataFrame()

    NOT_STOCK=False

    stock=Ticker(symbol)
    stock_data=stock.financial_data[symbol]
    print (stock_data)

    try:
        if "No fundamentals" in stock_data :
            NOT_STOCK=True
            stock_data=stock.price[symbol]
            currentPrice=stock_data['regularMarketPreviousClose']
        else:
            try:
                currentPrice=stock_data['currentPrice']
                targetHighPrice=stock_data['targetHighPrice']
                targetLowPrice=stock_data['targetLowPrice']
            except:
                NOT_STOCK=True
    except:
        pass


    # plot_chart(df,'Close',axes)

    try:
        df=pd.read_csv(expanduser(dir_path+'/'+symbol+'_'+'option_chain(split 1)'+'.csv'),  header=None, index_col=0, skiprows=1)
    except:
        print (symbol,' has no Option Chain, program abort.')
        return

    df.columns=df.loc['contractSymbol']
    df=df[df.index!='contractSymbol']

    df=df.T

    df.to_csv(dir_path+'/'+symbol+'_tmp_optionchain.T.csv')
    for col in df.columns:
        try:
            df[col] = df[col].astype(float)
        except:
            continue


    pivot_df = pd.pivot_table(df,index=['strike'],
                              columns=['optionType'],
                              values= ['volume', 'openInterest'],
                              aggfunc='sum'
                              )
    pivot_df.to_csv('pivot_df.csv')
    dates_formatted = [pd.to_datetime(d) for d in df['expiration']]
    x = [ (d-min(dates_formatted)).days for d in dates_formatted]
    df['expiration'] = (pd.to_datetime(df['expiration'],utc=True)).dt.date

    LowLim=min(pivot_df.index)
    HighLim=max(pivot_df.index)


# =============================================================================
#     PLOT CHART
# =============================================================================

    fig = plt.figure(figsize=(12, 6),dpi=600)
    grid = plt.GridSpec(4, 4, hspace=0.1, wspace=0.1)
    main_ax = fig.add_subplot(grid[:-1, 1:])#,projection='3d')
    left_ax = fig.add_subplot(grid[:-1, 0],  sharey=main_ax)#xticklabels=[],
    bottom_ax = fig.add_subplot(grid[-1, 1:], sharex=main_ax)#yticklabels=[],
    main_ax.grid(True, color='grey',linewidth=0.2)
    left_ax.grid(True, color='grey',linewidth=0.2)
    bottom_ax.grid(True, color='grey',linewidth=0.2)
    # main_ax.set_facecolor('silver')

# =============================================================================
#     # Main chart
# =============================================================================
# =============================================================================
#     for i in range(len(pivot_df)):
#         strike=pivot_df.index[i]
#         df_calls_at_strike=df[['openInterest','expiration','strike']].loc[(df['optionType']=='calls') & (df['strike']==strike) & (df['openInterest']>0)]
#         df_puts_at_strike=df[['openInterest','expiration','strike']].loc[(df['optionType']=='puts') & (df['strike']==strike) & (df['openInterest']>0)]
#         # https://matplotlib.org/stable/api/markers_api.html
#         main_ax.scatter(df_puts_at_strike['expiration'], df_puts_at_strike['strike'], alpha=0.5, s=8,color='red', marker='x', label='puts',zorder=100)
#         main_ax.scatter(df_calls_at_strike['expiration'], df_calls_at_strike['strike'], alpha=0.5, s=8 , color='darkgreen', marker='+', label='calls',zorder=100)
# =============================================================================
    df_calls_at_strike=df[['openInterest','expiration','strike']].loc[(df['optionType']=='calls')  & (df['openInterest']>0)]
    df_puts_at_strike=df[['openInterest','expiration','strike']].loc[(df['optionType']=='puts')  & (df['openInterest']>0)]
    main_ax.scatter(df_calls_at_strike['expiration'], df_calls_at_strike['strike'], alpha=1, s=9, color='green', marker='o', label='calls',zorder=100)
    main_ax.scatter(df_puts_at_strike['expiration'], df_puts_at_strike['strike'], alpha=1, s=9,color='red', marker='.', label='puts',zorder=100)

    # main_ax.xaxis.set_major_locator(mdates.MonthLocator())
    # main_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m/%d'))

    main_ax.axhline(currentPrice,color='steelblue',label='current price='+str(currentPrice),linewidth=1.5,alpha=0.5,zorder=120)

    # new_ticks=df['expiration'].unique()
    # main_ax.set_xticks(new_ticks)
    # main_ax.set_xticklabels(new_ticks,rotation=90,fontsize=6)
    # main_ax.set_xticklabels([])
    # main_ax.set_yticklabels([])


    # =============================================================================
    #     # Left chart
    # =============================================================================
    # priceprofiledf=round_and_group(df)
    left_ax.set_ylabel('Strike Price', fontsize = 9)
    left_ax.set_xlabel('volume', fontsize = 8)

    if NOT_STOCK:
        bar_width=2
    else:
        bar_width=round(((targetHighPrice-targetLowPrice) / len(pivot_df.loc[(pivot_df.index>targetLowPrice) & (pivot_df.index<targetHighPrice)]))*0.8,1)

    # print ((targetHighPrice-targetLowPrice))
    # print (len(pivot_df.loc[(pivot_df.index>targetLowPrice) & (pivot_df.index<targetHighPrice)]))
    # print (((targetHighPrice-targetLowPrice) / len(pivot_df.loc[(pivot_df.index>targetLowPrice) & (pivot_df.index<targetHighPrice)])))

    left_ax.barh(pivot_df.index, pivot_df[('volume','calls')], color='darkgreen', alpha=0.5, label='calls', height=bar_width, edgecolor = "white",linewidth=0.2,zorder=100)
    left_ax.barh(pivot_df.index, pivot_df[('openInterest','calls')], color='green', alpha=0.5, left=pivot_df[('volume','calls')],label='OIcalls', height=bar_width, edgecolor = "white",linewidth=0.2,zorder=100)
    left_ax.barh(pivot_df.index, pivot_df[('volume','puts')], color='firebrick', alpha=0.5, left=pivot_df[('volume','calls')]+pivot_df[('openInterest','calls')], label='puts', height=bar_width,edgecolor = "white", linewidth=0.2,zorder=100)
    left_ax.barh(pivot_df.index, pivot_df[('openInterest','puts')], color='red', alpha=0.5, left=pivot_df[('volume','calls')]+pivot_df[('openInterest','calls')]+pivot_df[('volume','puts')],  label='OIputs', height=bar_width,edgecolor = "white",linewidth=0.2,zorder=100)

    formatter = FuncFormatter(thousands)
    left_ax.xaxis.set_major_formatter(formatter)
    left_ax.locator_params(axis="y", nbins=10)
    left_ax.locator_params(axis="x", nbins=3)
    # left_ax.set_facecolor('silver')

    # =============================================================================
    #   left_ax: SET TICKS for data
    # =============================================================================

    if not NOT_STOCK:
        price_bracket=patches.Rectangle(xy=(0,targetLowPrice), height=targetHighPrice-targetLowPrice+1, width=max(pivot_df[('volume','calls')]+pivot_df[('openInterest','calls')]+pivot_df[('openInterest','puts')]+pivot_df[('volume','puts')])+1, linestyle='--', linewidth=0.8, edgecolor='firebrick', facecolor='none', zorder=120)
        left_ax.add_patch(price_bracket)
        # left_ax.set_ylim(LowLim-1,HighLim+1)
        # left_ax.set_ylim(targetLowPrice-1,targetHighPrice+1)
        left_ax.set_ylim(currentPrice*0.8,currentPrice*1.2)


    # =============================================================================
    #     # Bottom chart
    # =============================================================================

    df_calls_at_strike=df[['expiration','openInterest','volume']].loc[(df['optionType']=='calls')]
    df_puts_at_strike=df[['expiration','openInterest','volume']].loc[(df['optionType']=='puts')]

    df_calls_at_strike=df_calls_at_strike.groupby('expiration').sum()
    df_puts_at_strike=df_puts_at_strike.groupby('expiration').sum()

    bottom_ax.bar(df_calls_at_strike.index, df_calls_at_strike['openInterest'], width=5, alpha=0.5, color='green', label='OIcalls', zorder=100)
    bottom_ax.bar(df_puts_at_strike.index, df_puts_at_strike['openInterest'], width=5,  alpha=0.5, color='red',bottom=df_calls_at_strike['openInterest'], label='OIputs', zorder=100)
    bottom_ax.set_xlabel('expiration date', fontsize = 8)
    bottom_ax.set_ylabel('open Interest', fontsize = 8)
    # bottom_ax.set_facecolor('silver')

# =============================================================================
#   bottom_ax: SET TICKS for data
# =============================================================================

    new_ticks=df['expiration'].unique()
    bottom_ax.set_xticks(new_ticks)
    bottom_ax.set_xticklabels(new_ticks,rotation=90,fontsize=5)

    new_ticks=(df_calls_at_strike['openInterest']+df_puts_at_strike['openInterest']).sort_values(ascending=False)
    bottom_ax.set_yticks(new_ticks)
    bottom_ax.set_yticklabels(new_ticks,fontsize=5)
    formatter = FuncFormatter(thousands)
    bottom_ax.yaxis.set_major_formatter(formatter)


# =============================================================================


    # main_ax.get_xaxis().set_visible(True)
    # main_ax.get_yaxis().set_visible(True)
    left_ax.get_xaxis().set_visible(True)
    left_ax.get_yaxis().set_visible(True)
    bottom_ax.get_xaxis().set_visible(True)
    bottom_ax.get_yaxis().set_visible(True)

    main_ax.legend(labelcolor='black',fontsize='small',frameon=False)#loc='lower right',
    left_ax.legend(labelcolor='black',fontsize='small', frameon=False)#loc='lower right',
    bottom_ax.legend(labelcolor='black',fontsize='small', frameon=False)#loc='lower right',
    remove_duplicate_label(main_ax)

    if  NOT_STOCK:
        plt.suptitle(symbol+' '+today_str,fontsize=12)
    else:
        plt.suptitle(symbol+' '+today_str+'/'+str(targetLowPrice)+'~'+str(targetHighPrice),fontsize=12)

    plt.tight_layout()
    plt.show()
    fig.savefig(expanduser(dir_path)+'/'+symbol+'.jpg',bbox_inches='tight')
    print('image saved:',expanduser(dir_path)+'/'+symbol+'.jpg')

def chatgpt():
    import openai
    import secret

    # Your OpenAI API key
    api_key=OPEN_AI_KEY

    # Set the API key
    openai.api_key = api_key
    print(api_key)

    # Function to send CSV file to ChatGPT for analysis
    def analyze_csv_with_chatgpt(csv_file_path):
        # Read CSV file
        with open(csv_file_path, 'r') as file:
            csv_content = file.read()

        # Specify the prompt to start the conversation
        prompt = f"Analyzing CSV file:\n{csv_content}\n\n---\n\n"
        # llm = OpenAI(model_name=“gpt-3.5-turbo-instruct”)

        # Generate response using ChatGPT
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-1106",
            prompt=prompt,
            max_tokens=150,
            temperature=0.7
        )

        # Extract and return the generated analysis
        return response.choices[0].text.strip()

    # Example usage:
    csv_file_path = '/Users/michaelwai/Dropbox (HK)/pypy/medium/trading/yahooquery_everything/MARA.2024-02-16/MARA_option_chain(split 1).csv'
    analysis_result = analyze_csv_with_chatgpt(csv_file_path)
    print(analysis_result)


if __name__ == '__main__':

    dir_path='./'+symbol+'.'+today_str

    answer=input('Do you want to download again data? Let me know stock ticker or press<enter> if not. ')
    print ('ok !')
    if answer:
        print ('working:',answer)
        symbol=answer.upper()
        dir_path='./'+symbol+'.'+today_str

        ticker = Ticker(symbol)#,asynchronous=True)
        print (Ticker.__dict__.keys() )
        print (expanduser('./'+dir_path))

        os.makedirs(expanduser(dir_path), exist_ok=True)

        df_module = query_module(ticker)
        if query_finance(ticker):
            show_option_chain()
    else:
        print ('working:',symbol)
        show_option_chain()

    query_screener()






