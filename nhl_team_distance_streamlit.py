# -*- coding: utf-8 -*-
"""
NEED TO ADD COMMENTS
"""

#Get some packages
import streamlit as st
import geopy
import pandas as pd
import numpy as np
from haversine import haversine,Unit
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

def get_schedule(year):
    #Now let's read in the schedule for the chosen season from hockey-reference using pandas.
    #We want the first table that it scrapes
    df_sched = pd.read_html('https://www.hockey-reference.com/leagues/NHL_'+year+'_games.html')[0]

    #There are a few games in niether team's home arena in 2023 that are easily handled. These are
    #recorded in the Notes column. The NHL's Global Series and other international games date
    #back to 1993 but no good info is available from hockey-reference until 2022-2023 so
    #we ignore these games. Fill all of the normal games with 'none'

    df_sched['Notes'] = df_sched['Notes'].fillna('none')
    df_sched['City'] = 'none'
    df_sched['State'] = 'none'

    #2022-2023 season had a few international games
    if year == '2023':
        #Edit the neutral game site Notes to only include the location so it can be fed
        #into the locator
        df_sched.loc[df_sched['Notes'] == 'at (Prague, CZ)',['City','State']] = ['Prague', 'CZ']
        df_sched.loc[df_sched['Notes'] == 'at Nokia Arena (Tampere, FI)',['City','State']] = ['Tampere', 'FI']
        df_sched.loc[df_sched['Notes'] == 'at Fenway Park (Boston, MA)',['City','State']] = ['Boston', 'MA']
        df_sched.loc[df_sched['Notes'] == 'at Carter-Finley Stadium (Raleigh, NC)',['City','State']] = ['Raleigh', 'NC']
    else:
        df_sched['Notes'] = 'none'
        
    return df_sched

#Cache the distance function so it speeds up if run on the same year twice
@st.cache
def calculate_distance(df_sched,df_teams):

    #Instantiate locator in case it's needed
    locator = geopy.geocoders.Nominatim(user_agent="myGeocoder")    

    #Loop through all games in the schedule
    for i in range(len(df_sched)):
        
        home_team = df_sched.iloc[i]['Home']
        visiting_team = df_sched.iloc[i]['Visitor']
        
        #Check for weird game notes and find where the game is being played
        if df_sched.iloc[i]['Notes'] != 'none':
            
            end_location = (locator.geocode(df_sched.iloc[i]['City']+', '+df_sched.iloc[i]['State']).latitude,
                           locator.geocode(df_sched.iloc[i]['City']+', '+df_sched.iloc[i]['State']).longitude)
            
        else:
            
            end_location = (df_teams.loc[df_teams['team'] == home_team,'latitude'].iloc[0],
                            df_teams.loc[df_teams['team'] == home_team,'longitude'].iloc[0])
            
        #Where did the teams start from?
        start_home_team = (df_teams.loc[df_teams['team'] == home_team,'last_latitude'].iloc[0],
                     df_teams.loc[df_teams['team'] == home_team,'last_longitude'].iloc[0])
        start_visiting_team = (df_teams.loc[df_teams['team'] == visiting_team,'last_latitude'].iloc[0],
                     df_teams.loc[df_teams['team'] == visiting_team,'last_longitude'].iloc[0])
        
        distance_home_team = haversine(start_home_team,end_location,unit=Unit.MILES)
        distance_visiting_team = haversine(start_visiting_team,end_location,unit=Unit.MILES)
        
        df_teams.loc[df_teams['team'] == visiting_team,'distance_traveled'] = df_teams.loc[df_teams['team'] == visiting_team,'distance_traveled'].iloc[0]+distance_visiting_team        
        df_teams.loc[df_teams['team'] == home_team,'distance_traveled'] = df_teams.loc[df_teams['team'] == home_team,'distance_traveled'].iloc[0]+distance_home_team        
            
        #Update df with new values
        df_teams.loc[df_teams['team'] == home_team,['last_latitude','last_longitude']] = [end_location[0],end_location[1]]
        df_teams.loc[df_teams['team'] == visiting_team,['last_latitude','last_longitude']] = [end_location[0],end_location[1]]
    
    #Remove any teams that didn't exist at the time and then sort according to distance traveled.
    #We eliminate teams that didn't exist by removing any teams that had no distance traveled
    df_teams = df_teams[df_teams['distance_traveled'] > 0]
    df_teams.sort_values('distance_traveled',ascending=False,inplace=True)

    return df_teams

def make_distance_plot(df,year,my_team):
    
    #Set a couple of variables
    nteams = len(df)
    fname = 'Arial'
    
    #Make distance bar plot.
    cmap = matplotlib.cm.get_cmap('bone')
    norm = matplotlib.colors.Normalize(vmin = min(df['longitude']),vmax = max(df['longitude']))
    
    fig = plt.figure(figsize=(20,12))
    ax = fig.add_subplot(1,1,1)
    im1 = plt.bar(np.linspace(0,nteams-1,num = len(df['team'])),df['distance_traveled'],
            label = df['team'],color = cmap(norm(df['longitude'])),width = 0.7, edgecolor = 'gray')
    plt.xticks([])
    plt.title('NHL team distance traveled '+str(int(year)-1)+'-'+year,fontsize = 25, fontname=fname)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['top'].set_visible(False)
    ax.set_ylabel('Distance traveled (miles)',fontsize=30,fontname=fname)
    ax.set_xlim([-1,nteams+1])
    ymax = max(df['distance_traveled'])*1.1
    ax.set_ylim([0,ymax])
    ax.tick_params(which = 'major', labelsize = 20)
    for tick in ax.get_yticklabels():
        tick.set_fontname('Arial')
    
    axins1 = ax.inset_axes([.55,.85,.35,.05])
    axins1.text(0, 1.12, 'West',fontsize=20,fontname=fname)
    axins1.text(1.0, 1.12, 'East',fontsize=20,horizontalalignment = 'right',fontname=fname)
    cbar = fig.colorbar(matplotlib.cm.ScalarMappable(cmap=cmap), cax=axins1, 
                 orientation="horizontal")
    cbar.set_ticks([])
    cbar.set_label(label = 'Longitude',size=25,fontname=fname)
    
    #Insert team logos at top of each bar
    t_off = -.01*ymax
    doff = .03*ymax
    ioff = .25
    for i,team in enumerate(df['team']):
        team_str = (team.replace(' ','_') + '.webp').lower()
        image = plt.imread('team_logos/' + team_str)
        im_zoom = 0.05
        #Nordiques PNG is a bit wider and needs to be scaled down
        if team_str == 'quebec_nordiques.webp':
            im_zoom = .03
        ax.add_artist(AnnotationBbox(
                OffsetImage(image,zoom=im_zoom), (i , df.iloc[i]['distance_traveled'] + doff),
                frameon=False) )
        if team == my_team:
            tcolor = 'red'
            fsize = '20'
        else:
            tcolor = 'black'
            fsize = 15
        ax.text(i+ioff, t_off, team, rotation = 45, horizontalalignment = 'right',
               verticalalignment = 'top', fontsize = fsize, fontname=fname, color = tcolor)
    
    fig.savefig('nhl_distance_traveled.png',bbox_inches = 'tight')
    
    return #fig    
    
#Now begin Streamlit implementation
st.title('NHL team distance traveled')
st.subheader('Ever wondered how far your favorite NHL team travels in a season?')
st.markdown('Just enter the year that the season of interest ends in (ex. 2023'+
             ' for the current 2022-2023 season) and check the resulting chart. For '+
            'information on the assumptions and a Jupyter Notebook version check out '+
            'the Github page: https://github.com/pwcauley/nhl-distance-traveled/')
year = st.text_input("Enter the season you want to look at:",value='')
st.caption('Only years after 1993 are valid!')
if year:
    if (float(year) > 1993) and year != '2005':
        
        df = pd.read_pickle("nhl_team_location_data.pkl")
        df_sched = get_schedule(year)
        team_series = np.insert(np.sort(df_sched['Visitor'].unique()),0,['(Select an option)','None'])
        team_of_interest = st.selectbox('Choose a team of interest (or None):',(team_series))
        st.caption('Selected team will be highlighted in red on the distance chart.')

        if team_of_interest != '(Select an option)':
            with st.spinner('Calculating distances...'):
            
                df_teams = calculate_distance(df_sched,df)
                distance_diff = int(df_teams['distance_traveled'].max() - df_teams['distance_traveled'].min())
                distance_fig = make_distance_plot(df_teams,year,team_of_interest)
                st.image('nhl_distance_traveled.png')
                st.markdown('* Average team distance traveled was '+str(int(df_teams['distance_traveled'].mean()))+' miles.')
                st.markdown('* The team that traveled the most traveled '+str(distance_diff)+' miles more than the team that traveled the least.')
                if team_of_interest != 'None':
                    toi_index = pd.Index(df_teams['team']).get_loc(team_of_interest)
                    toi_distance = int(df_teams[df_teams['team'] == team_of_interest]['distance_traveled'])
                    toi_percent = str(int((len(df_teams)-(toi_index+1))*100/len(df_teams)))
                    toi_text = '* The <span style="color:Red;">'+team_of_interest+'</span> traveled '+str(toi_distance)+' miles, which is more than '+toi_percent+'\% of teams that season.'
                    st.markdown(toi_text,unsafe_allow_html=True)

    elif year == '2005':
        st.markdown('Unfortunately, there was a lockout during 2004 - 2005 and the '+
                'entire season and postseason were canceled. Try another year!')
    else:
        st.markdown('Only years after 1993 are valid! Sorry, Minnesota North Stars fans...')
    
