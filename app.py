from flask_cors import CORS
from flask import Flask, request, jsonify, Response
import requests
from bs4 import BeautifulSoup
import json
import os
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

OLLAMA_API_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_API_MODEL = "llama3.2"

def parse_llm_response(response):
    # Parse JSON to extract all responses
    responses = []
    buffer = ''
    for i, char in enumerate(response):
        buffer += char
        if char == '}':
            try:
                parsed = json.loads(buffer)
                if 'response' in parsed:
                    responses.append(parsed['response'])
                buffer = ''
            except json.JSONDecodeError:
                # If we hit an error, keep building the buffer until we can parse it
                continue

    # Join all responses to get the full text
    full_text = ''.join(responses)

    # Extract summary and sentiment
    summary = []
    sentiment = None
    
    # Extract summary points
    summary_pattern = r'([*\u2022]) (.+?)\n'
    summary_matches = re.findall(summary_pattern, full_text)
    for match in summary_matches:
        summary.append(match[1].strip())
    
    # Extract sentiment
    sentiment_match = re.search(r'Sentiment:\s*(\w+)', full_text)
    if sentiment_match:
        sentiment = sentiment_match.group(1).lower()  # Convert to lowercase for consistency

    return summary, sentiment

@app.route('/analyze', methods=['POST'])
def analyze_urls():
    try:
        data = request.get_json()
        urls = data.get('urls')
        if not urls:
            return jsonify({'error': 'No URLs provided'}), 400

        results = []
        for url in urls:
            try:
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.title.string
                article_text = ' '.join(soup.get_text().split())

                llm_response = requests.post(
                    OLLAMA_API_ENDPOINT,
                    json={"model": OLLAMA_API_MODEL,
                          "prompt": f"""
Article content:
{article_text}

Please summarize this article in exactly 2-3 sentences using bullet points. Then, provide the sentiment of the summary with one of these words: positive, neutral, negative. Format your response like this:

Summary:
- [Sentence 1]
- [Sentence 2]
- [Sentence 3] (optional)

Sentiment: [positive, neutral, or negative]
""",
                          "option": {"num_ctx": 100000}
                    },
                    timeout=180
                )
                llm_response.raise_for_status()
                print (f"LLM Response:{llm_response.text}")
                summary, sentiment = parse_llm_response(llm_response.text)
                
                if summary:
                    print("Summary:")
                    for point in summary:
                        print(point)
                else:
                    print("Summary not found.")

                if sentiment:
                    print("\nSentiment:", sentiment)
                else:
                    print("\nSentiment not found.")

                results.append({
                    'name': title,
                    'summary': summary,
                    'sentiment': sentiment,
                    'url': url,
                })

            except requests.exceptions.RequestException as e:
                return jsonify({'error': f'Error fetching URL {url}: {e}'}), 500
            except json.JSONDecodeError as e:
                return jsonify({'error': f'Error decoding Ollama response for {url}: {e}'}), 500
            except Exception as e:
                return jsonify({'error': f'An unexpected error occurred processing {url}: {e}'}), 500
        return jsonify(results)

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON input: {e}'}), 400
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500


if __name__ == '__main__':
    app.run(debug=True)
