import re
from flask import Flask, request, jsonify
from flask_cors import CORS  # Importa CORS
from pymongo import MongoClient
from bs4 import BeautifulSoup
import requests
import re
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Configuración de MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['eltiempo_comments']
news_collection = db['news']

# Inicializar Flask
app = Flask(__name__)
CORS(app, origins=["http://20.64.242.135:3000"])  # Habilitar CORS para todas las rutas

# Inicializar el analizador de VADER
analyzer = SentimentIntensityAnalyzer()

# Función para hacer scraping de la noticia
def scrape_news_data(news_url):
    try:
        # Hacer la solicitud a la página
        response = requests.get(news_url)
        if response.status_code != 200:
            return None, f"Error: {response.status_code}"

        # Parsear el contenido HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extraer título
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Sin título"
        
        # Extraer lead desde og:description
        lead = soup.find('meta', property='og:description')
        lead = lead['content'].strip() if lead and 'content' in lead.attrs else "Sin lead"
        
        # Extraer ID de la URL (ignorar el símbolo #)
        news_id_match = re.search(r'-(\d+)(?:#|$)', news_url)
        news_id = news_id_match.group(1) if news_id_match else "ID no encontrado"

        return {
            'title': title,
            'lead': lead,
            'url': news_url,
            'id': news_id
        }, None
    except Exception as e:
        return None, str(e)

# Función para procesar los comentarios pegados manualmente
def process_comments(raw_comments):
    processed_comments = []
    current_author = "Anonymous"  # Valor por defecto si no hay autor
    current_date = "Sin fecha"    # Valor por defecto si no hay fecha

    # Cambiamos la separación para reconocer los saltos de línea
    lines = raw_comments.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Ignorar comentarios que comienzan con "Respuesta de"
        if line.lower().startswith("respuesta de"):
            continue
        
        # Detectamos comentarios con la palabra clave "Comentario de"
        if line.lower().startswith('comentario de'):
            current_author = line.replace('Comentario de', '').strip('. ')
        
        # Detectamos la fecha de los comentarios, buscando el patrón "Hace x horas/días"
        elif re.match(r'hace.*', line, re.IGNORECASE):
            current_date = line
        
        # Para cualquier otro tipo de línea, la tomamos como contenido del comentario
        elif line and not line.lower() == 'anuncio':  # Ignoramos la palabra "Anuncio"
            processed_comments.append({
                'author': current_author,
                'date': current_date,
                'content': line
            })
            # Restablecemos el autor y la fecha solo cuando se ha procesado un comentario
            current_author = "Anonymous"  # Restablecemos el autor
            current_date = "Sin fecha"    # Restablecemos la fecha

    return processed_comments


# Función para analizar el sentimiento de un comentario usando VADER
def analyze_sentiment(comment):
    score = analyzer.polarity_scores(comment)
    if score['compound'] >= 0.05:
        return 'positivo'
    elif score['compound'] <= -0.05:
        return 'negativo'
    else:
        return 'neutral'

# Función para categorizar la noticia
def categorize_news(title, lead):
    categories = {
        'política': ['política', 'gobierno', 'elecciones', 'congreso', 'partidos', 'corrupcion'],
        'deportes': ['deportes', 'fútbol', 'baloncesto', 'atletismo', 'equipo'],
        'tragedias': ['tragedia', 'accidente', 'muerte', 'desastre', 'heridos'],
        'entretenimiento': ['entretenimiento', 'cine', 'música', 'espectáculos', 'celebridades'],
    }

    combined_text = f"{title.lower()} {lead.lower()}"
    
    for category, keywords in categories.items():
        if any(keyword in combined_text for keyword in keywords):
            return category  # Retorna la categoría que coincide

    return 'otros'

# Ruta para recibir la URL de la noticia y los comentarios
@app.route('/comments', methods=['POST'])
def add_comments():
    data = request.json
    news_url = data.get('url')
    raw_comments = data.get('comments')

    if not news_url or not raw_comments:
        return jsonify({'message': 'URL de la noticia y comentarios son requeridos'}), 400

    # Realizar el scraping de la noticia
    news_data, error = scrape_news_data(news_url)
    if error:
        return jsonify({'message': f'Error al obtener la noticia: {error}'}), 500

    # Procesar los comentarios pegados manualmente
    processed_comments = process_comments(raw_comments)

    # Analizar el sentimiento de cada comentario
    for comment in processed_comments:
        comment['sentiment'] = analyze_sentiment(comment['content'])

    # Categorizar la noticia
    news_data['category'] = categorize_news(news_data['title'], news_data['lead'])

    # Guardar los datos de la noticia y los comentarios en MongoDB
    news_collection.insert_one({
        'news_data': news_data,
        'comments': processed_comments
    })

    return jsonify({'message': 'Noticia y comentarios guardados con éxito'}), 201

# Ruta para obtener la noticia y los comentarios por ID
@app.route('/comments/id/<string:news_id>', methods=['GET'])
def get_comments_by_id(news_id):
    news_data = news_collection.find_one({'news_data.id': news_id})
    if not news_data:
        return jsonify({'message': 'No se encontraron datos para este ID'}), 404
    
    return jsonify(news_data), 200

# Ruta para borrar la noticia y comentarios por ID
@app.route('/comments/id/<string:news_id>', methods=['DELETE'])
def delete_comments_by_id(news_id):
    result = news_collection.delete_one({'news_data.id': news_id})
    
    if result.deleted_count == 0:
        return jsonify({'message': 'No se encontraron datos para borrar este ID'}), 404
    
    return jsonify({'message': 'Noticia y comentarios borrados con éxito'}), 204

@app.route('/comments/stats/<string:news_id>', methods=['GET'])
def get_sentiment_stats_by_id(news_id):
    news_data = news_collection.find_one({'news_data.id': news_id})
    
    if not news_data:
        return jsonify({'message': 'No se encontraron datos para este ID'}), 404

    comments = news_data['comments']
    total_comments = len(comments)
    
    if total_comments == 0:
        return jsonify({'message': 'No hay comentarios para esta noticia'}), 404

    positive_comments = [c for c in comments if c['sentiment'] == 'positivo']
    negative_comments = [c for c in comments if c['sentiment'] == 'negativo']
    neutral_comments = [c for c in comments if c['sentiment'] == 'neutral']

    num_positive = len(positive_comments)
    num_negative = len(negative_comments)
    num_neutral = len(neutral_comments)

    unique_users = len(set([c['user_id'] for c in comments if 'user_id' in c]))

    sentiment_scores = {
        'positivo': 5,
        'neutral': 3,
        'negativo': 1
    }
    total_sentiment_score = sum([sentiment_scores[c['sentiment']] for c in comments])
    overall_sentiment = total_sentiment_score / total_comments

    sentiment_breakdown = {
        'positive': (num_positive / total_comments) * 100,
        'neutral': (num_neutral / total_comments) * 100,
        'negative': (num_negative / total_comments) * 100
    }

    return jsonify({
        'title': news_data['news_data'].get('title', 'Título no disponible'),
        'lead': news_data['news_data'].get('lead', 'Lead no disponible'),
        'category': news_data['news_data'].get('category', 'Categoría no disponible'),
        'overallSentiment': overall_sentiment,
        'totalComments': total_comments,
        'uniqueUsers': unique_users,
        'sentimentBreakdown': sentiment_breakdown,
        'comments': comments
    }), 200


# Iniciar el servidor Flask
if __name__ == '__main__':
    app.run(debug=True)
