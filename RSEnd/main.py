from flask import Flask, json, request, jsonify
from flask_cors import CORS

DEBUG = True
from PIL import Image
from api.map_analysis import map_analysis_bp
from api.change_detection备份 import change_detection_bf_bp
from api.history import history_bp
from api.road_extraction import road_extraction_bp
from api.object_detection import object_detection_bp
from api.land_segmentation import land_segmentation_bp


app = Flask(__name__)
app.config.from_object(__name__)
CORS(app, resource={r'/*': {'origins': '*'}})

app.register_blueprint(change_detection_bf_bp, url_prefix='/api/change_detection')
app.register_blueprint(history_bp, url_prefix='/api/history')
app.register_blueprint(road_extraction_bp, url_prefix='/api/road_extraction')
app.register_blueprint(object_detection_bp, url_prefix='/api/object_detection')
app.register_blueprint(land_segmentation_bp, url_prefix='/api/land_segmentation')
app.register_blueprint(map_analysis_bp, url_prefix='/api/map_analysis')

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True)