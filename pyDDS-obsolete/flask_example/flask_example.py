import flask
app = flask.Flask(__name__)

@app.route('/')
def index():
    global amplitude
    global phase
    global frequency
    return flask.render_template('dds.html', amplitude=amplitude, phase=phase, frequency=frequency)

@app.route('/set_apf/<int:channel>', methods=['POST', 'GET'])
def set_APF(channel):
    global amplitude
    global phase
    global frequency
    r = flask.request.form
    amplitude = float(r['amplitude'])
    phase = float(r['phase'])
    frequency = float(r['frequency'])
    print('setting amplitude=%g, phase=%g, frequency=%g for channel %d' % (amplitude, phase, frequency, channel))
    return flask.redirect(flask.url_for('index'))


@app.route('/shutdown', methods=['POST', 'GET'])
def shutdown():
    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    global amplitude
    global phase
    global frequency
    amplitude=1
    phase=0
    frequency=10
    app.run(port=80)
