import time
import argparse
from sgqlc.operation import Operation

from config.shiphero_schema import shiphero_schema
from utils.common import get_grapql_endpoint, save_json_file

FILTER_FROM_DATE = "2024-08-01"
FILTER_DATE_TO = None
FILTER_LIMIT = 100
REQUEST_INTERVAL = 10

parser = argparse.ArgumentParser()
parser.add_argument("--datefrom", help="Order date from filter")
parser.add_argument("--dateto", help="Order date to filter")
parser.add_argument("--limit",
                    help="Number of shipments extracted per request")
parser.add_argument("--interval", help="Seconds to wait before each request")
args = parser.parse_args()
if args.datefrom:
    FILTER_FROM_DATE = str(args.datefrom)
if args.dateto:
    FILTER_DATE_TO = str(args.dateto)
if args.limit:
    FILTER_LIMIT = int(args.limit)
if args.interval:
    REQUEST_INTERVAL = int(args.interval)


def extract_shipments(from_date, date_to=None, limit=10, after=''):
    """Shiphero Data Extractor"""
    graphql = get_grapql_endpoint()
    op = Operation(shiphero_schema.Query)
    if date_to:
        query = op.shipments(order_date_from=from_date, order_date_to=date_to)
    else:
        query = op.shipments(order_date_from=from_date)
    query.complexity()

    query_data = query.data(first=limit, after=after)
    select = query_data.edges.node
    select.id()
    select.legacy_id()
    select.order_id()
    select.user_id()
    select.warehouse_id()
    select.pending_shipment_id()
    select.profile()
    select.picked_up()
    select.completed()
    select.created_date()
    select.total_packages()

    query_data.page_info.has_next_page()
    query_data.page_info.end_cursor()
    return graphql(op)


start = time.time()
print('Extracting shipments...')


GO_TO_NEXT_PAGE = True
PAGE_COUNT = 0
NEXT_PAGE = ''
TOTAL_COMPLEXITY = 0
FAILS = 0
shipments = []

while GO_TO_NEXT_PAGE:
    print(f"Extracting page: {str(PAGE_COUNT+1)}           ", end='\r')
    try:
        data = extract_shipments(from_date=FILTER_FROM_DATE,
                                 date_to=FILTER_DATE_TO,
                                 limit=FILTER_LIMIT,
                                 after=NEXT_PAGE)
        # if "errors" in data:
        #     print(data['errors'][0]['message'])
        data = data['data']['shipments']
        for order in data['data']['edges']:
            shipments.append(order['node'])
        TOTAL_COMPLEXITY += data['complexity']
        page_info = data['data']['pageInfo']
        GO_TO_NEXT_PAGE = page_info['hasNextPage']
        NEXT_PAGE = page_info['endCursor']
        PAGE_COUNT += 1
    except Exception as e:
        FAILS += 1
        print(
            f"Failed to extract data | Retrying in {REQUEST_INTERVAL}s | Error: {str(e)}")
    if GO_TO_NEXT_PAGE:
        for i in range(REQUEST_INTERVAL):
            count = f"{'0' if (REQUEST_INTERVAL-i)<REQUEST_INTERVAL else ''}{REQUEST_INTERVAL - i}"
            print(f"Page {PAGE_COUNT} extracted. Waiting {count}s", end='\r')
            time.sleep(1)

print(f'Shipments count: {len(shipments)}     ')
print(
    f'Total complexity: {TOTAL_COMPLEXITY} ({PAGE_COUNT} requests/{FAILS} fails)')


if shipments:
    print("Saving to file...")
    save_json_file('data/shipments', shipments)
    print("data saved to file!")

print(f'Extraction completed --- time taken: {(time.time()-start)} sec')
