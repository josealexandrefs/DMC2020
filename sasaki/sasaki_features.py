import os
import pandas as pd
import numpy as np


orders= pd.read_csv('../main/datasets/1.0v/orders.csv', sep = '|')
items= pd.read_csv('../main/datasets/1.0v/items.csv', sep = '|')

import sys
sys.path.append("../main")

from utils import read_data, process_time, merge_data


def remove_itemID_not_used(items, orders):
    """removes from item.csv the rows with item without sales"""
    id_used = orders.itemID.unique()

    boolean = [np.isin(idd,id_used) for idd in items.itemID]
    items= items[boolean] 
    
    return items




def add_feature_promotion(items, orders):
    """ add to orders.csv and items.csv:
        modeSalesPrice: the sales price mode of rows with same itemID
        
        add to orders.csv:
        difModa: error between modeSalesPrice and salesPrice
        """
    
    def _get_mode_sales_price(id):
        sales_id_certo = orders[orders['itemID'] == id]
        mode = sales_id_certo['salesPrice'].mode()

        #a moda pode ter mais de um valor, 
        #para torna-la um unico foi escolhido arbitrariamente a mediana
        return mode.median()
    
    
    items['modeSalesPrice'] =items['itemID'].map(_get_mode_sales_price )
    
    modeSalesPrice = items[['itemID','modeSalesPrice']]
    orders = pd.merge(orders, modeSalesPrice, on='itemID')
    
    
    orders['difModa'] = orders['salesPrice'] - orders['modeSalesPrice']

    return items, orders
    

def agregating_by_week(items, orders,add_zero_salues=False, time_processed=True, promotion_added=True):
    """ agregate orders.csv by week , itemID and salesPrice
        if add_zero_salues is true, add rows of itemID in every week, even if the total sales is zero
        """
        
    
    if ( time_processed == False):
        process_time(orders)
    
    if ( promotion_added == False):
        items, orders = add_feature_promotion(items, orders)
        
    
    orders["week_backward"] = np.ceil(orders["days_backwards"] / 7).astype(int)
    
    #removing the first week, it has 5 days only
    orders = orders[orders["week_backward"]!=26]
    

    #agregating by week
    orders_w = orders.groupby(['itemID','salesPrice','week_backward']).agg({'order' : ['sum'], 
                                                               'group_backwards' : ['mean'],
                                                               'modeSalesPrice' : ['mean'], 
                                                               'difModa' : ['mean']})
    orders_w = orders_w.reset_index()
    orders_w.columns = ['itemID','salesPrice','week_backward','order','group_backwards','modeSalesPrice','difModa']
    
    
    if(add_zero_salues):
        weeks_database = orders['week_backward'].unique()
        new_rows = []
        
        for idd in items['itemID'].unique():
            orders_id = orders_w[orders_w.itemID == idd]
            example = orders_id.iloc[0]
    
            #finding weeks without itemID sales
            weeks_id = orders_id['week_backward'].unique()
            weeks_without_id = np.setdiff1d(weeks_database , weeks_id)
    
            #creating new row
            for w in weeks_without_id:
                new_rows.append({'itemID':idd, 
                                 'salesPrice':example['modeSalesPrice'], 
                                 'week_backward':w, 
                                 'order':0,
                                 'group_backwards':example['group_backwards'], 
                                 'modeSalesPrice':example['modeSalesPrice'], 
                                 'difModa':example['difModa']
                                })

        orders_w = orders_w.append(new_rows) 

        
    return orders_w


def add_feature_position_month(orders, time_processed=True, timeScale='group_backwards'):
    """ add to orders.csv:
        posM_f_group: position in the month of the first day of the group
        posM_m_group: position of the midle day of the group
        posM_l_group: position of the last day
        
        if add_feature_week:
        also add the 3 features above but for the week
        
        #path = path to the position_in_month.csvs
        """
    
    if time_processed == False:
        process_time(orders)
    
    positions = pd.read_csv('position_in_month.csv')  
    
    
    if timeScale=='group_backwards':
        positions = positions.groupby('group_backwards').first()
        positions = positions.drop(columns=['posM_f_week','posM_m_week','posM_l_week','week_backwards'])
    if timeScale=='week_backwards':
        positions = positions.drop(columns=['posM_f_group','posM_m_group','posM_l_group','group_backwards'])
     
    comb = pd.merge(orders, positions, on=timeScale, how='left')
    

        
    return comb