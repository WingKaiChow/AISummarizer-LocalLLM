from flask_cors import CORS
from flask import Flask, request, jsonify, Response
import requests
from bs4 import BeautifulSoup
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

OLLAMA_API_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_API_MODEL = "llama3.2"

@app.route('/analyze', methods=['POST'])
def analyze_urls():
    try:
        data = request.get_json()
        print (f"data: {data}")
        urls = data.get('urls')
        print (f"urls: {urls}")
        if not urls:
            return jsonify({'error': 'No URLs provided'}), 400

        results = []
        for url in urls:
            try:
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                article_text = ' '.join(soup.get_text().split())
                print (f"article_text:{article_text}")

                llm_response = requests.post(
                    OLLAMA_API_ENDPOINT,
                    json={"model":  OLLAMA_API_MODEL,
                          "prompt": f"""
Summarize the following article in three concise sentences, presented as bullet points:

{article_text}
""",
                          "option":{
                            "num_ctx": 100000
                          }
                    },
                    timeout=180
                )
                print(f"Response Text: {llm_response.text}")
                llm_response.raise_for_status()
                print (f"llm_response.raise_for_status(): {llm_response.raise_for_status()}")
                #llm_data = llm_response.json()
                # Example usage:
                llm_data = process_streamed_response(llm_response.text)
                print (f"llm_data: {llm_data}")

                #sentiment = llm_data.get('sentiment', 'N/A')
                #print (f"sentiment: {sentiment}")
                #summary = llm_data.get('summary', 'N/A')
                #print (f"summary: {summary}")
                
                results.append({
                    'name': url.split('/')[-1],
                    'summary': llm_data,
                    'sentiment': "N/A",
                    'url': url,
                })

            except requests.exceptions.RequestException as e:
                print (f"e: {e}")
                return jsonify({'error': f'Error fetching URL {url}: {e}'}), 500
            except json.JSONDecodeError as e:
                print (f"e: {e}")
                return jsonify({'error': f'Error decoding Ollama response for {url}: {e}'}), 500
            except Exception as e:
                print (f"e: {e}")
                return jsonify({'error': f'An unexpected error occurred processing {url}: {e}'}), 500

        return jsonify(results)

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON input: {e}'}), 400
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

def process_streamed_response(response_text):
    response = ""
    for line in response_text.splitlines():
        try:
            # Parse each line as JSON
            data = json.loads(line)
            
            # Append the 'response' field to our accumulated response
            response += data['response']
            
            # Check if this is the last chunk
            if data['done']:
                print("\nFinal Response:")
                print(response)
                print(f"Done Reason: {data.get('done_reason', 'Unknown')}")
                print(f"Context: {data.get('context', 'No context provided')}")
                print(f"Total Duration: {data.get('total_duration', 'Not available')} ns")
                print(f"Load Duration: {data.get('load_duration', 'Not available')} ns")
                print(f"Prompt Eval Count: {data.get('prompt_eval_count', 'Not available')}")
                print(f"Prompt Eval Duration: {data.get('prompt_eval_duration', 'Not available')} ns")
                print(f"Eval Count: {data.get('eval_count', 'Not available')}")
                print(f"Eval Duration: {data.get('eval_duration', 'Not available')} ns")
                break  # Exit the loop if 'done' is True
        
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for line: {line}")
    
    return response

if __name__ == '__main__':
    app.run(debug=True)
