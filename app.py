import os
import cv2
import json
import pandas as pd

import condition_assignment_pipnet
import main_fixation_pipnet

from flask import Flask
from flask import request, send_from_directory

from PIPNet.pipnet import PIPNet

app = Flask(__name__)
pipnet = None



@app.before_first_request
def initialize():
    global pipnet
    pipnet = PIPNet()


@app.route("/process", methods=["GET", "POST"])
def process():
    assert request.form['participant'] != ''
    participant_id = request.form['participant']

    video = request.files['video']
    fixations = request.files['fixations']

    starting_hours = processTime(request.form['starting-hours'])
    starting_minutes = processTime(request.form['starting-minutes'])
    starting_seconds = processTime(request.form['starting-seconds'])

    ending_hours = processTime(request.form['ending-hours'])
    ending_minutes = processTime(request.form['ending-minutes'])
    ending_seconds = processTime(request.form['ending-seconds'])

    video_path = 'tmp.mp4'
    video.save(video_path)
    print('Saved video')

    fixations_path = 'fixations.csv'
    fixations.save(fixations_path)
    print('Saved fixations')
    
    # conditions
    print('Processing conditions ...')
    frame_start, frame_end = condition_assignment_pipnet.getStartAndEndFrame(video_path, starting_hours, starting_minutes, starting_seconds, ending_hours, ending_minutes, ending_seconds)
    condition_result = condition_assignment_pipnet.processFrames(video_path, pipnet, frame_start, frame_end)
    condition_result = condition_assignment_pipnet.filterNoiseFace(condition_result, kernel_size=3)  # only interested in longer periods of closed eyes
    condition_result = condition_assignment_pipnet.filterNoiseEyes(condition_result, kernel_size=15)  # only interested in longer periods of closed eyes
    df_conditions = pd.DataFrame(condition_result)
    df_conditions.to_excel('conditions_pipnet.xlsx')
    print('Processed conditions')
    
    # fixations
    print('Processing fixations ...')
    df_fixations = pd.read_csv(fixations_path)
    df_result = main_fixation_pipnet.processFixations(video_path, df_fixations, df_conditions, pipnet, frame_start, frame_end, participant_id)
    df_result.to_excel(f'mapping_{participant_id}.xlsx')
    print('Processed fixations')

    return send_from_directory('.', f'mapping_{participant_id}.xlsx', as_attachment=True)


def processTime(t):
    if t == '':
        return 0

    t = int(t)
    return t