from datetime import datetime, timedelta
from collections import defaultdict, deque
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def build_graph(flights):
    graph = defaultdict(list)
    for flight in flights:
        departure_time = datetime.fromisoformat(flight['departureTimestamp'].replace('Z', '+00:00'))
        arrival_time = datetime.fromisoformat(flight['arrivalTimestamp'].replace('Z', '+00:00'))
        graph[flight['fromAirportIata']].append((flight, departure_time, arrival_time))
    return graph

def find_flights_with_stops(flights, date, from_iata, to_iata):
    try:
        date = datetime.fromisoformat(date.replace('Z', '+00:00'))
    except ValueError as e:
        logging.error(f"Invalid date format: {date} - Error: {e}")
        return []

    graph = build_graph(flights)
    paths = []
    queue = deque([(from_iata, [], datetime.min, 0, 0)])

    while queue:
        current_airport, path, prev_arrival, total_price, total_duration = queue.popleft()
        for flight, departure_time, arrival_time in graph[current_airport]:
            if departure_time.date() != date.date():
                continue
            if prev_arrival != datetime.min and (departure_time - prev_arrival < timedelta(minutes=30) or departure_time - prev_arrival > timedelta(hours=4)):
                continue
            if any(f['fromAirportIata'] == current_airport for f in path):
                continue
            new_path = path + [flight]
            new_price = total_price + flight['price']
            new_duration = total_duration + flight['duration']
            if flight['toAirportIata'] == to_iata:
                paths.append((new_path, new_price, new_duration))
            else:
                queue.append((flight['toAirportIata'], new_path, arrival_time, new_price, new_duration))

    return paths

@app.route('/flights', methods=['POST'])
def find_flights():
    data = request.get_json()
    flights = data['flights']
    date_str = data['date']
    from_iata = data['fromIata']
    to_iata = data['toIata']

    logging.debug(f"Received request data: {data}")

    paths = find_flights_with_stops(flights, date_str, from_iata, to_iata)

    valid_paths = []
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError as e:
        logging.error(f"Invalid date format: {date_str} - Error: {e}")
        return jsonify({"error": "Invalid date format"}), 400

    for path, price, duration in paths:
        if path and datetime.fromisoformat(path[0]['departureTimestamp'].replace('Z', '+00:00')).date() == date.date() and datetime.fromisoformat(path[-1]['arrivalTimestamp'].replace('Z', '+00:00')).date() == date.date():
            valid_paths.append((path, price, duration))

    valid_paths.sort(key=lambda x: (x[1], len(x[0]), x[2]))

    result = [[flight for flight in path] for path, _, _ in valid_paths]

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=8085)
