#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask,render_template,request
import spacy
import en_core_web_md
import pandas as pd
import requests
from datetime import date
from math import pi

from bokeh.layouts import gridplot
from bokeh.plotting import figure
from bokeh.palettes import Spectral10
from bokeh.models import LinearColorMapper, ColorBar
from bokeh.embed import components

Newsycle = Flask(__name__)
Newsycle.dt = ''

class EntityAnalysis:
    def __init__(self, name):
        self.name = name
        self.people = []
        self.gpe = []
        self.norp = []
        self.fac = []
        self.org = []
        self.loc = []
        self.product = []
        self.event = []
        self.work_of_art = []

    def initialize(self, descriptions):
        stopwords = ["America", "U.S.", "the United States", "US", \
                     "American"]
        for doc in nlp.pipe(descriptions):
            for ent in doc.ents:
                if ent.text in stopwords:
                    continue
                if ent.label_ == 'PERSON':
                    self.people.append(ent.text)
                if ent.label_ == 'GPE':
                    self.gpe.append(ent.text)
                if ent.label_ == 'NORP':
                    self.norp.append(ent.text)
                if ent.label_ == 'FAC':
                    self.fac.append(ent.text)
                if ent.label_ == 'ORG':
                    self.org.append(ent.text)
                if ent.label_ == 'LOC':
                    self.loc.append(ent.text)
                if ent.label_ == 'PRODUCT':
                    self.product.append(ent.text)
                if ent.label_ == 'EVENT':
                    self.event.append(ent.text)
                if ent.label_ == 'WORK_OF_ART':
                    self.work_of_art.append(ent.text)

        # these may be useful later
        self.people_count = pd.Series(self.people).value_counts()
        self.gpe_count = pd.Series(self.gpe).value_counts()
        self.norp_count = pd.Series(self.norp).value_counts()
        self.fac_count = pd.Series(self.fac).value_counts()
        self.org_count = pd.Series(self.org).value_counts()
        self.loc_count = pd.Series(self.loc).value_counts()
        self.product_count = pd.Series(self.product).value_counts()
        self.event_count = pd.Series(self.event).value_counts()
        self.work_of_art_count = pd.Series(self.work_of_art).value_counts()

        # this is useful now (Newsycle 1.0)
        self.all_ent_list = sum([self.people, self.gpe, self.norp, self.fac, self.org, \
                                 self.loc, self.product, self.event, self.work_of_art], [])
        self.all_ents_freq = pd.Series(self.all_ent_list).value_counts()

def get_articles(source, dt):
    url = ('https://newsapi.org/v2/everything?sources={0}&language=en&from={1}&to={1}&pageSize=100&apiKey=c7b94c4920914da1bf5b712b0d16b061'.format(source, dt))
    return requests.get(url)

# have to reverse colors here (before the plot function def) to make blue on top
colors = Spectral10
colors.reverse()

def ent_freq_plot(EA):
    words = list(EA.all_ents_freq[9::-1].index)
    name = EA.name
    p = figure(y_range=words, plot_height=350, plot_width=700, title="%s Top Mentions"\
               % name.upper(), tools="hover,save,reset")
    p.hbar(y=words, right=EA.all_ents_freq[9::-1].values, height=0.45, \
           fill_color=colors)
    p.yaxis.major_label_text_font_size = '1.2em'
    p.yaxis.major_label_text_font = 'sans-serif'
    p.title.text_font = 'sans-serif'
    p.title.text_font_size = '1.2em'
    p.ygrid.grid_line_color = None
    p.yaxis.major_tick_line_color = None
    p.xaxis.minor_tick_line_color = None
    p.x_range.start = 0
    return p

def get_similarity(ea1, ea2):
    a = nlp(' '.join(list(ea1.all_ents_freq[:10].index)))
    b = nlp(' '.join(list(ea2.all_ents_freq[:10].index)))
    return a.similarity(b)

# load the spaCy model
nlp = en_core_web_md.load()

# select the media outlets (change to app variable?)
media = ['the-new-york-times', 'the-washington-post', 'cnn', 'fox-news', \
         'breitbart-news', 'the-wall-street-journal']

@Newsycle.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        Newsycle.dt = str(request.form['dt'])
    else: 
        Newsycle.dt = str(date.today())
    # create and fill a dict of lists of article descriptions 
    article_dict = {}
    for outlet in media:
        response = get_articles(outlet, Newsycle.dt)
        article_dict[outlet] = [response.json()['articles'][i]['description'] \
                                for i in range(len(response.json()['articles']))]
        # remove any None returns from API
        article_dict[outlet] = [desc for desc in article_dict[outlet] if desc != None]
    
    # analyze entities for each media outlet
    ea1, ea2, ea3, ea4, ea5, ea6 = (EntityAnalysis(outlet) for outlet in media)
    EAs = (ea1, ea2, ea3, ea4, ea5, ea6)
    ea1.initialize(article_dict[media[0]])
    ea2.initialize(article_dict[media[1]])
    ea3.initialize(article_dict[media[2]])
    ea4.initialize(article_dict[media[3]])
    ea5.initialize(article_dict[media[4]])
    ea6.initialize(article_dict[media[5]])
    
    # compute similarities
    sim_list = [get_similarity(i, j) for i in EAs for j in EAs]
    
    # create DataFrame for heatmap
    sim_df = pd.DataFrame(sim_list, columns=['sim'])
    tmp = []
    for outlet in media:
        tmp.append(outlet)          # this can be refactored,
        tmp.append(outlet)          # but it does what I want for now
        tmp.append(outlet)
        tmp.append(outlet)
        tmp.append(outlet)
        tmp.append(outlet)
    sim_df['x'] = tmp
    sim_df['y'] = media * 6
    
    #create heatmap
    mapper = LinearColorMapper(palette=colors, low=sim_df.sim.min()-0.2, high=sim_df.sim.max())
    hm = figure(title='News Topic Similarity Between Outlets on {0}'.format(Newsycle.dt), \
                    x_range=media, y_range=media, plot_width=850, plot_height=450, \
                    tooltips=[('Similarity', '@sim')], tools="tap,save,reset")
    hm.xaxis.major_label_orientation = pi / 6
    hm.xaxis.major_label_text_font_size = '1.2em'
    hm.xaxis.major_label_text_font = 'sans-serif'
    hm.xaxis.major_label_text_font_style = 'bold'
    hm.yaxis.major_label_text_font_size = '1.2em'
    hm.yaxis.major_label_text_font = 'sans-serif'
    hm.yaxis.major_label_text_font_style = 'bold'
    hm.yaxis.major_tick_line_color = None
    hm.xaxis.major_tick_line_color = None
    hm.title.text_font = 'sans-serif'
    hm.title.text_font_size = '1.2em'
    hm.rect(x='x', y='y', width=1, height=1, source=sim_df, \
            fill_color={'field':'sim', 'transform':mapper}, line_color=None)
    color_bar = ColorBar(color_mapper=mapper, location=(0,0))
    hm.add_layout(color_bar, 'right')
    # create entity freq plots
    m1, m2, m3, m4, m5, m6 = (ent_freq_plot(ea) for ea in EAs)        
    p = gridplot([[m1, m2], 
                  [m3, m4],
                  [m5, m6]], toolbar_location='right', sizing_mode='scale_width')
    script, div = components(p)
    script2, div2 = components(hm)
    return render_template('graph.html', script=script, div=div, \
                           script2=script2, div2=div2, date=Newsycle.dt)


if __name__ == "__main__":
    Newsycle.run(debug=True)
