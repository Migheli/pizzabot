from moltin_api_handlers import get_all_entries
from geopy import distance


def get_min_distance_to_customer(moltin_token, flow_slug, customer_coordinates):
    entries = get_all_entries(moltin_token, flow_slug)
    distances_to_customer = []
    for entry in entries:
        entry_coordinates = (entry['longitude'], entry['latitude'])
        distance_to_customer = distance.distance(entry_coordinates, customer_coordinates).km
        distances_to_customer.append(distance_to_customer)
    return min(distances_to_customer)


def get_distance_to_customer(entry_dataset):
    return entry_dataset['distance_to_customer']


def get_nearest_entry(entries, customer_coordinates):
    entries_datasets = []
    for entry in entries:
        entry_dataset = {}
        entry_coordinates = (entry['longitude'], entry['latitude'])
        entry_dataset['address'] = entry['address']
        entry_dataset['id'] = entry['id']
        distance_to_customer = distance.distance(entry_coordinates, customer_coordinates).km
        entry_dataset['distance_to_customer'] = distance_to_customer
        entries_datasets.append(entry_dataset)
    return min(entries_datasets, key=get_distance_to_customer)


def get_location(update):
    return update.message.location.latitude, update.message.location.longitude


def fetch_coordinates(geocoder_key, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": YANDEX_GEOCODER_KEY,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat