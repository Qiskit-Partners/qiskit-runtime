# Qiskit Runtime Test Server

The test server exposes the Qiskit Runtime API locally. It is intended for
developing and testing cloud services relying on quantum computations. The test
server uses Qiskit Aer simulators instead of real devices.

The test server API mimicks the real Qiskit Runtime API found at:
https://runtime-us-east.quantum-computing.ibm.com/openapi/#/

A tutorial on how to access the REST API directly can be found at:
https://github.com/Qiskit-Partners/qiskit-runtime/blob/main/tutorials/API_direct.ipynb

Uploading programs to the test server is not supported via API, but it is
possible to configure [new programs with minimal effort](#new-programs).

## Quick setup

The easiest way to run the test server is to build and run the Docker image
in this repository. Thus, [install Docket](https://docs.docker.com/get-docker/)
and run the following command to build the image:

    docker build -t qiskitruntime:latest .

And to run the Docker container:

    docker run \
      --rm -d --name qr-test-server \
      --volume="$(pwd)"/qiskit_runtime:/qiskit-runtime/qiskit_runtime \
      --volume="$(pwd)"/logs:/qiskit-runtime/logs \
      -p 8000:8000 \
      -e "NUM_WORKERS=4" \
      qiskitruntime:latest \
      bash start-test-server.sh

The previous command mounts the `qiskit_runtime` and `logs` directories from the
current repository to the container so any change you do in these directories
will be reflected in the container.

The previous configuration allows up to 4 programs to be run at the same time.
If you want to change this number, you can use the `NUM_WORKERS` environment
variable. For example, to run 8 programs simultaneously, you can use:

    docker run \
      --rm -d --name qr-test-server \
      --volume="$(pwd)"/qiskit_runtime:/qiskit-runtime/qiskit_runtime \
      --volume="$(pwd)"/logs:/qiskit-runtime/logs \
      -p 8000:8000 \
      -e "NUM_WORKERS=8" \
      qiskitruntime:latest \
      bash start-test-server.sh

If you want to stop the container, you can run:

    docker stop qr-test-server

## Installation

The test server relies on Redis for the asynchrnous execution of programs. The
easiest way to run Redis is inside a docker container. Grab the image from:

    docker pull redis

And run it, exposing the default Redis port:

    docker run -d --name qr-test-server-redis -p 6379:6379 redis

With Redis running, you can install the test server dependencies from the root
of the repository:

    pip install -r requirements.txt
    pip install -r requirements-server.txt

## Running the server

[Ensuring Redis is running](#installation) before starting the server.

In a terminal session, and from the root of the repository, use the following
command to run the workers in charge  of running the Qiskit Runtime programs.

    python qiskit_runtime/test_server/worker.py

If you want multiple programs to run concurrently, you can launch multiple
workers.

In a different terminal, also from theroot of the repository, use the following
command to run the test server:

    uvicorn qiskit_runtime.test_server:runtime --reload --reload-dir qiskit_runtime

The `--reload --reload-dir qiskit_runtime` option will reload the server when
any of the files inside the `qiskit_runtime` directory change. This is usful if
you are developing a new Qiskit Runtime program.

Explore the API documentation by visiting http://127.0.0.1:8000/docs

### Executing the `sample-program` program

List all available programs:

    curl -X 'GET' \
      'http://127.0.0.1:8000/programs' \
      -H 'accept: application/json'

Run the sample program:

    curl -X 'POST' \
      'http://127.0.0.1:8000/jobs' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "programId": "sample-program",
      "hub": "string",
      "group": "string",
      "project": "string",
      "backend": "string",
      "params": [
        "{\"iterations\":2000}"
      ]
    }'

It will answer with the job id, take note of it and now onwards, replace
`<job_id>` with the actual job id. To get the status of the job, run:

    curl -X 'GET' \
      'http://127.0.0.1:8000/jobs/<job_id>' \
      -H 'accept: application/json'

Read the logs of the job with:

    curl -X 'GET' \
      'http://127.0.0.1:8000/jobs/<job_id>/logs' \
      -H 'accept: application/json'

And the result of the job with:

    curl -X 'GET' \
      'http://127.0.0.1:8000/jobs/<job_id>/results' \
      -H 'accept: application/json'

If you want to stream the logs of the job, the server exposes a websocket at:

    http://127.0.0.1:8000/stream/jobs/<job_id>

A quick way of testing it is to open a browser and use the developer tools:

1. Visit the API documentation at http://127.0.0.1:8000/docs
2. Open the JavaScript console and run the following command:

        new WebSocket('ws://localhost:8000/stream/jobs/<job_id>');

3. Navigate to the Network tab in the dev tools of your browser, filter by
   websocket, click the one with the `<job_id>` in the URL, and you should see
   the logs of the job in the response view of the request.

## New programs

Although you cannot use the API to upload programs, you can still expose your
own programs through the test server. Let's see how:

### Prerequisites

If you are thinking of creating your own programs, you may be interested in
following the same conventions we use at Qiskit Runtime. You can install the
development dependencies with:

    pip install -r requirements-dev.txt

### Program structure

Think of a name for your program, for example `Hello Quantum`. Come up with a
snake version of it, for example `hello_quantum`, and create new Python package
inside the `qiskit_runtime` folder.

The folder structure should look like this:

    qiskit_runtime
    └── hello_quantum
        ├── __init__.py
        ├── hello_quantum.json
        └── hello_quantum.py

### Setup an entry point

The entry point of your Qiskit Runtime program is a function called `main`.
Open `hello_quantum.py` and add the following code:

```python
from qiskit import QuantumCircuit


def prepare_bell_circuit():
    bell = QuantumCircuit(2, 2)
    bell.h(0)
    bell.cx(0, 1)
    bell.measure_all()
    return bell


def main(backend, messenger, greeting):
    bell = prepare_bell_circuit()  # prepare the circuits
    messenger.publish(greeting)  # publish interim results
    print(bell.draw(output='text'))  # draw the circuit (captured as part of the logs)
    result = backend.run(bell).result()  # run the circuit
    messenger.publish(result.get_counts(), final=True)  # publish the final result

```

The `main` function is always passed the `backend` and `messenger` positional
arguments and whatever named parameters you specify at the moment of scheduling
a new job.

Learn more about writing your own programs by reading the
"Constructing a runtime program" section at the
["Uploading a Qiskit runtime program" tutorial](https://github.com/Qiskit-Partners/qiskit-runtime/blob/main/tutorials/02_uploading_program.ipynb).

### Complete the mandatory metadata

Open `hello_quantum.json` and add the following content:

```json
{
  "name": "hello-quantum",
  "description": "A simple test program."
}
```

Learn more about writing filling-in the program metadata by reading the
"Defining program metadata" section at the
["Uploading a Qiskit runtime program" tutorial](https://github.com/Qiskit-Partners/qiskit-runtime/blob/main/tutorials/02_uploading_program.ipynb).

### Register and expose your program

Finally, open `qiskit_runtime/test_server/config.ini` and add the following line
at the end of the `[programs]` section:

    hello-quantum=qiskit_runtime.hello_quantum.hello_quantum

The **id of the program** is the name appearing before the `=` sign, while the
portion after the `=` is the full path to the Python package containing the
entry point.

Your `config.ini` file should look similar to this:

```ini
[programs]
circuit-runner=qiskit_runtime.circuit_runner.circuit_runner
quantum-kernel-alignment=qiskit_runtime.qka.qka
vqe=qiskit_runtime.vqe.vqe_program
sample-program=qiskit_runtime.sample_program.sample_program
hello-quantum=qiskit_runtime.hello_quantum.hello_quantum
```

The server checks for new changes in the `config.ini` file so adding new
programs does not require restarting the server (if running the server with
the `--reload` option, altering this file also causes the server to reload).

### Run the program

Try getting the metadata of the program:

    curl -X 'GET' \
      'http://127.0.0.1:8000/programs/hello-quantum' \
      -H 'accept: application/json'

    {
      "name": "hello-quantum",
      "cost": 600,
      "description": "A simple test program.",
      "version": "1.0",
      "backendRequirements": null,
      "parameters": null,
      "returnValues": null,
      "isPublic": true
    }

Schedule a new run of the program:

    curl -X 'POST' \
      'http://127.0.0.1:8000/jobs' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "programId": "hello-quantum",
      "hub": "string",
      "group": "string",
      "project": "string",
      "backend": "string",
      "params": ["{ \"greeting\":\"Hello Quantum!\" }"]
    }'

    {
      "id": "1fe35045-0341-444b-a796-6a9fbae512ac"
    }

Use the job id returned to you to get the logs of the job:

    curl -X 'GET' \
      'http://127.0.0.1:8000/jobs/1fe35045-0341-444b-a796-6a9fbae512ac/logs' \
      -H 'accept: application/json'


    "\"Hello Quantum!\"\n        ┌───┐      ░ ┌─┐   \n   q_0: ┤ H ├──■───░─┤M├───\n        └───┘┌─┴─┐ ░ └╥┘┌─┐\n   q_1: ─────┤ X ├─░──╫─┤M├\n             └───┘ ░  ║ └╥┘\n   c: 2/══════════════╬══╬═\n                      ║  ║ \nmeas: 2/══════════════╩══╩═\n                      0  1 \n{\"00 00\": 521, \"11 00\": 503}\n"

No, those symbols are not garbage, they are the result the ASCII art of the
circuit. Logs include anything printed to stdout and stderr, as well as the
interim results and the final result of the program.

For accessing the results only, you can use:

    curl -X 'GET' \
      'http://127.0.0.1:8000/jobs/1fe35045-0341-444b-a796-6a9fbae512ac/results' \
      -H 'accept: application/json'


    "{\"00 00\": 521, \"11 00\": 503}"

## Limitations

The current version of the test server does not support the following features:

- Cancelling jobs.
- Upload new programs via API.
- Group, hub and project configuration.
- Specifying the backend to use.

### API

Qiskit Runtime is still in beta mode, and heavy modifications to both
functionality and API are likely to occur. Some of the changes might not be
backward compatible and would require updating your Qiskit version.

## License

[Apache License 2.0](../LICENSE.txt)
