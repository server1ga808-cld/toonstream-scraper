# app.py - ToonStream Scraper API Server
import os
from flask import Flask, request, jsonify
from scraper import ToonStreamScraper

app = Flask(__name__)
scraper = ToonStreamScraper()


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "success": True,
        "message": "ToonStream Scraper API is running",
        "endpoints": {
            "search": "/api/search?q={query}",
            "episodes": "/api/episodes?slug={series_slug}",
            "streaming": "/api/streaming?slug={series_slug}&season={s}&episode={e}",
            "servers": "/api/servers?url={episode_url}"
        }
    })


@app.route('/api/search', methods=['GET'])
def search():
    """অ্যানিমে খোঁজার এন্ডপয়েন্ট।"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"success": False, "error": "Query parameter 'q' is required"}), 400

    try:
        results = scraper.search_anime(query)
        return jsonify({
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/episodes', methods=['GET'])
def episodes():
    """একটি সিরিজের সব এপিসোডের লিস্ট।"""
    slug = request.args.get('slug', '').strip()
    if not slug:
        return jsonify({"success": False, "error": "Parameter 'slug' is required"}), 400

    try:
        eps = scraper.get_episode_list(slug)
        return jsonify({
            "success": True,
            "series_slug": slug,
            "total_episodes": len(eps),
            "episodes": eps
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/streaming', methods=['GET'])
def streaming():
    """নির্দিষ্ট এপিসোডের সব স্ট্রিমিং লিংক (iframe embed URL)।"""
    slug = request.args.get('slug', '').strip()
    season = request.args.get('season')
    episode = request.args.get('episode')

    if not slug:
        return jsonify({"success": False, "error": "Parameter 'slug' is required"}), 400

    try:
        s = int(season) if season else None
        e = int(episode) if episode else None
        result = scraper.get_streaming_links(slug, s, e)
        status = 200 if result.get("success") else 404
        return jsonify(result), status
    except ValueError:
        return jsonify({"success": False, "error": "season and episode must be integers"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/servers', methods=['GET'])
def servers():
    """সরাসরি এপিসোড URL থেকে সব সার্ভারের লিংক।"""
    episode_url = request.args.get('url', '').strip()
    if not episode_url:
        return jsonify({"success": False, "error": "Parameter 'url' is required"}), 400

    try:
        result = scraper.get_servers(episode_url)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
