import json
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from search import get_meta_information, generate_new_data_from_gpt3, search

# Flask app
app = Flask(__name__)

###
# API endpoints


@app.route('/search', methods=['POST'])
def search_handler():
    search_query = request.json.get('query')

    ########################################
    # Step 1: Validating request
    if search_query is None:
        return jsonify({'error': 'Mandatory field "search" is missing'}), 400
    page_num = request.json.get('page', 1)

    # check if page number is valid
    if page_num < 1 or page_num > 10:
        return jsonify({'error': 'Page number must be between 1 and 10'}), 400

    #############
    # Step 2: Performing search
    print('Performing search for query: ' + search_query)
    results = search(search_query, advanced=True,
                     page=page_num, num_results=10)
    results = list(results)
    if len(results) == 0:
        return jsonify({'error': 'Something went wrong'}), 500
    elif results[0] is None:
        return jsonify({'error': 'No results found'}), 404
    print('* Found ' + str(len(results)) + ' results for query: ' + search_query + ' on page ' + str(page_num) + ' of Google')
    #############
    # Step 3: Extracting meta information
    meta_info = []
    for x in results:
        resp = get_meta_information(x.url)
        meta_info.append(resp)
    print('* Extracted meta information for ' + str(len(meta_info)) + ' results')

    #############
    # Step 4: Generating new data from GPT3
    new_meta_info = generate_new_data_from_gpt3(2, meta_info)
    print('* Generated new meta information for ' + str(len(new_meta_info)) + ' results')

    #############
    # Step 5: Returning results
    search_results = {
        'search_query': search_query,
        'page_num': page_num,
        'results': [{'url': result.url, 'title': result.title, 'description': result.description} for result in results] if results is not None else [],
        'num_results':  len(results),
        'meta_info': [{'meta_title': resp['meta_title'], 'meta_description': resp['meta_description'], 'meta_keywords': resp['meta_keywords']} for resp in meta_info],
        'gpt_meta_info': json.loads(new_meta_info["choices"][0]["message"]["content"])
    }
    print('* Returning results')
    return jsonify(search_results)


##
# Main method
##
if __name__ == '__main__':
    load_dotenv()
    # check for OPENAI_API_KEY
    if not os.environ.get('OPEN_AI_KEY'):
        print('OPENAI_API_KEY not found in .env file')
        exit(1)
    app.run(debug=True)
