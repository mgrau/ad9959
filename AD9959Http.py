"""Server for AD9959 running on RPi.

Make sure that flask and flask_autodoc are installed. Then replace add_custom_nl2br_filters(self, app) in 
<python-installation>\Lib\site-packages\flask_autodoc\autrodoc.py by
    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){3,}')

    @app.template_filter()
    @evalcontextfilter
    def nl2br(eval_ctx, value):
        result = '\n\n'.join('%s' % p.replace('\n', '<br>\n')
                             for p in _paragraph_re.split(escape(value)))
        if eval_ctx.autoescape:
            result = Markup(result)
        return result

For starting the server use (export instead of set in linux)
set FLASK_APP=<filename>
(set FLASK_DEBUG=True)
python -m flask run.
"""

import flask
from flask_autodoc import Autodoc
from AD9959 import AD9959
import json

app = flask.Flask(__name__)
auto = Autodoc(app)

DDS = AD9959()

@app.route('/set_ffpa', methods=['POST', 'GET'])
@auto.doc('public')
def fpa():
    pass



@app.route('/set_frequency', methods=['POST', 'GET'])
@auto.doc('public')
def outputs():
    """Manipulate the dac output.

    GET will return the current dac settings.

    POST will strip a dictionary from the url and set the dac channels accordingly.
    When channels were set correctly the current dac settings are returned. Otherwise
    the error message is returned.
    Arguments:
    out -- dict {<channel name>: <voltage>}
                 <channel name> can be 'A', 'B', 'C', 'D' or 'All'. 
                 <voltage> must be in [-10 V, 10 V].

    Returns (for GET and POST):
    dict {<channel name>: <voltage>}
          <channel name> 'A', 'B', 'C' and 'D'. 
          <voltage> in [-10 V, 10 V].
    """

    if DAC is not None:
        if flask.request.method == "POST":
            input_data = flask.request.args.to_dict()

            try:
                resp = DAC.set_outputs(input_data)
            except AD5764Error as e:
                resp = {'error': e.args[0]}
            except Exception as e:
                resp = {'error': 'An unknown error occured. Message: ' + str(e.args)}
        else: # GET
            resp = DAC.get_current_output()
    else:
        resp = {'error': 'Could not initialize AD5764.'}

    return json.dumps(resp)

@app.route('/ramp', methods=['POST', 'GET'])
@auto.doc('public')
def ramp():
    """Ramps the output of one output channel from v1 to v2 in a time T. Maximum update rate is 20 kHz.

    Arguments:
    channel -- valid channel name ('A', 'B', 'C', 'D' or 'All')
    v1 -- valid voltage in [-10V, 10V]
    v2 -- valid voltage in [-10V, 10V]
    T -- ramp duration in seconds. Must be larger than 50 us

    Returns:
    state of DAC after ramp or error message in case an error occured.
    """

    input_data = flask.request.args.to_dict()
    try:
        DAC.ramp_output(input_data['channel'], input_data['v1'], input_data['v2'], input_data['T'])
        resp = DAC.get_current_output()
    except KeyError:
        resp = {'error': 'Invalid arguments.'}
    except AD5764Error as e:
        resp = {'error': e.args[0]}

    return json.dumps(resp)

@app.route('/push_sequence', methods=['POST', 'GET'])
@auto.doc('public')
def push_sequence():
    """Adds a sequence to the sequence stack.

    A sequence consists of a list of dictionarys corresponding to the DAC outputs at each time step and a list of time steps. 
    The new sequence is compared with the sequence stack and the new states are inserted at the right timing positions.

    When using TTL pulses to advance the sequence have the TTL input high. On each falling edge the DAC will change it's output 
    and on the subsequent rising edge the next state will be written to the DAC. Note that the SPI communication takes around 30 us
    per 3 bytes written to the DAC, hence you should wait at least <number of updated channels> * 30 us before triggering the next
    output of the sequence.

    Be careful when using internal timing since the program is locked until the sequence finished. TTL triggered sequences can be
    cancelled at any time using AD5764.cleanup_sequence.

    After running an internally triggered sequence AD5764 is again in a state where you can write outputs to the DAC using AD5764.set_output.
    TTL triggered sequences need to be either manually set back to that state by using AD5764.cleanup_sequence or by sending an additional 
    falling edge at the end of the sequence. This will trigger AD5764.cleanup_sequence once to reset AD5764.

    Arguments:
    sequence -- list [{<channel> : <voltage}, ...] containing the state of the DAC at each sequence step.
                       <channel> can be 'A', 'B', 'C', 'D' or 'All'.
                       <voltage> must be in [-10 V, 10 V]. 
                       If in one timestep a channel is omitted, the previous output state will be maintained.
                       Adding a channel that is already set at a certain time in the sequence stack will override the output.
    timing -- A time-ordered list [t_0, t_1, ...] containing the timing relative to the first event (negative times are allowed).
              len(timing) != len(sequence)

    Returns:
    The complete sequence when no error occured. Otherwise the error message.
    """

    input_data = flask.request.args.to_dict(False)

    try:
        timing = json.loads(input_data['timing'][0])
        sequence = json.loads(input_data['sequence'][0])
        resp = DAC.push_sequence(sequence, timing)
    except KeyError:
        resp = {'error': 'Invalid input arguments for push_sequence.'}
    except AD5764Error as e:
        resp = {'error': e.args[0]}

    return json.dumps(resp)

@app.route('/run_sequence', methods=['POST', 'GET'])
@auto.doc('public')
def run_sequence():
    """Prepares the RPi for running a sequence.

    Either prepares the TTL input for an externally triggered sequence or runs the sequence with internal timing.

    When using TTL pulses to advance the sequence have the TTL input high. On each falling edge the DAC will change it's output 
    and on the subsequent rising edge the next state will be written to the DAC. Note that the SPI communication takes around 30 us
    per 3 bytes written to the DAC, hence you should wait at least <number of updated channels> * 30 us before triggering the next
    output of the sequence.

    Be careful when using internal timing since the program is locked until the sequence finished. TTL triggered sequences can be
    cancelled at any time using AD5764.cleanup_sequence.

    After running an internally triggered sequence AD5764 is again in a state where you can write outputs to the DAC using AD5764.set_output.
    TTL triggered sequences need to be either manually set back to that state by using AD5764.cleanup_sequence or by sending an additional 
    falling edge at the end of the sequence. This will trigger AD5764.cleanup_sequence once to reset AD5764.
    
    Arguments:
    mode -- 'ext' or 'int'. Defines whether the sequence is externally or internally timed.
    """

    input_data = flask.request.args.to_dict()

    try:
        resp = DAC.run_sequence(input_data['mode'])
    except KeyError:
        resp = {'error': 'Invalid arguments for run_sequence.'}
    except AD5764Error as e:
        resp = {'error': e.args[0]}

    return json.dumps(resp)

@app.route('/cleanup', methods=['POST', 'GET'])
@auto.doc('public')
def cleanup():
    """Removes any sequence from the queue and resets the DAC.

    After calling this function the DAC is reset s.t. channels can be again directly set by /set_outputs.
    """

    DAC.cleanup_sequence()

    return json.dumps(True)


@app.route('/')
def redirect():
    """Redirects to documentation. """

    return flask.redirect('/doc')

@app.route('/doc')
def documentation():
    """Shows the documentation rendered by autodoc. """

    return auto.html('public', title='AD5764 doc')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

