#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import os
import random

from flask import Flask, render_template


app = Flask(__name__, template_folder='./src/web/templates')


@app.route('/')
def index():

	return render_template('index.html')

if __name__ == "__main__":

    app.run(use_reloader=True, debug=True)







