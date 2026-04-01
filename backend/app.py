from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import pandas as pd
import os
import sqlite3
import json
from datetime import datetime
import time
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# Database setup with timeout and check_same_thread
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'predictions.db')

def get_db_connection():
    """Get database connection with proper settings"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
    return conn

# Get paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Model paths
model_folder = os.path.join(project_root, 'model')
model_path = os.path.join(model_folder, 'ridge_model.pkl')
scaler_path = os.path.join(model_folder, 'scaler.pkl')
encoders_path = os.path.join(model_folder, 'label_encoders.pkl')
imputation_path = os.path.join(model_folder, 'imputation_values.pkl')
feature_info_path = os.path.join(model_folder, 'feature_info.pkl')

# Load training data
train_data_path = os.path.join(current_dir, 'data', 'train.csv')
train_df = pd.read_csv(train_data_path)

# Load models
print("Loading models...")
model = joblib.load(model_path)
scaler = joblib.load(scaler_path)
label_encoders = joblib.load(encoders_path)
imputation_values = joblib.load(imputation_path)
feature_info = joblib.load(feature_info_path)
print("✅ Models loaded successfully!")

# Calculate statistics
mean_price = train_df['SalePrice'].mean()
median_price = train_df['SalePrice'].median()
std_price = train_df['SalePrice'].std()
min_price = train_df['SalePrice'].min()
max_price = train_df['SalePrice'].max()

# Initialize database with correct schema
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create predictions table with all required columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            predicted_price REAL,
            formatted_price TEXT,
            confidence_lower REAL,
            confidence_upper REAL,
            formatted_lower TEXT,
            formatted_upper TEXT,
            input_features TEXT,
            all_features TEXT,
            vs_average_diff TEXT,
            vs_average_percent TEXT,
            actual_price REAL,
            is_verified INTEGER DEFAULT 0,
            user_rating INTEGER,
            added_to_training INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# Initialize database
init_db()

@app.route('/')
def home():
    return jsonify({
        'message': 'Ames House Price Prediction API',
        'model': 'Ridge Regression',
        'features': len(feature_info['features']),
        'training_samples': len(train_df),
        'avg_price': f"${mean_price:,.0f}"
    })

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    return jsonify({
        'mean_price': float(mean_price),
        'median_price': float(median_price),
        'std_price': float(std_price),
        'min_price': float(min_price),
        'max_price': float(max_price),
        'total_houses': len(train_df),
        'avg_living_area': float(train_df['GrLivArea'].mean()),
        'avg_lot_area': float(train_df['LotArea'].mean()),
        'avg_qual_rating': float(train_df['OverallQual'].mean()),
        'avg_garage_cars': float(train_df['GarageCars'].mean()),
        'avg_year_built': float(train_df['YearBuilt'].mean())
    })

@app.route('/api/price-distribution', methods=['GET'])
def get_price_distribution():
    prices = train_df['SalePrice'].tolist()
    return jsonify({'prices': prices})

@app.route('/api/correlation-matrix', methods=['GET'])
def get_correlation_matrix():
    numeric_features = train_df.select_dtypes(include=[np.number]).columns.tolist()
    if 'Id' in numeric_features:
        numeric_features.remove('Id')
    correlation_matrix = train_df[numeric_features].corr().round(2)
    return jsonify({
        'features': numeric_features,
        'matrix': correlation_matrix.values.tolist()
    })

@app.route('/api/feature-correlation', methods=['GET'])
def get_feature_correlation():
    key_features = ['SalePrice', 'GrLivArea', 'TotalBsmtSF', 'LotArea',
                    'OverallQual', 'YearBuilt', 'GarageCars', 'FullBath',
                    'BedroomAbvGr', 'Fireplaces', 'WoodDeckSF', 'OpenPorchSF']
    correlation_matrix = train_df[key_features].corr().round(2)
    return jsonify({
        'features': key_features,
        'matrix': correlation_matrix.values.tolist()
    })

@app.route('/api/feature-importance', methods=['GET'])
def get_feature_importance():
    coefficients = model.coef_
    feature_names = feature_info['all_features']
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': np.abs(coefficients)
    }).sort_values('importance', ascending=False).head(20)
    return jsonify({
        'features': importance_df['feature'].tolist(),
        'importance': importance_df['importance'].tolist()
    })

@app.route('/api/price-by-neighborhood', methods=['GET'])
def get_price_by_neighborhood():
    neighborhood_stats = train_df.groupby('Neighborhood')['SalePrice'].agg(['mean', 'median', 'count', 'std']).reset_index()
    neighborhood_stats = neighborhood_stats.sort_values('mean', ascending=False)
    return jsonify({
        'neighborhoods': neighborhood_stats['Neighborhood'].tolist(),
        'means': neighborhood_stats['mean'].tolist(),
        'medians': neighborhood_stats['median'].tolist(),
        'counts': neighborhood_stats['count'].tolist(),
        'stds': neighborhood_stats['std'].tolist()
    })

@app.route('/api/price-over-time', methods=['GET'])
def get_price_over_time():
    yearly_stats = train_df.groupby('YearBuilt')['SalePrice'].agg(['mean', 'median', 'count']).reset_index()
    return jsonify({
        'years': yearly_stats['YearBuilt'].tolist(),
        'means': yearly_stats['mean'].tolist(),
        'medians': yearly_stats['median'].tolist(),
        'counts': yearly_stats['count'].tolist()
    })

@app.route('/api/price-by-quality', methods=['GET'])
def get_price_by_quality():
    quality_stats = train_df.groupby('OverallQual')['SalePrice'].agg(['mean', 'min', 'max', 'count', 'std']).reset_index()
    return jsonify({
        'qualities': quality_stats['OverallQual'].tolist(),
        'means': quality_stats['mean'].tolist(),
        'mins': quality_stats['min'].tolist(),
        'maxs': quality_stats['max'].tolist(),
        'counts': quality_stats['count'].tolist(),
        'stds': quality_stats['std'].tolist()
    })

@app.route('/api/scatter-data', methods=['GET'])
def get_scatter_data():
    x_feature = request.args.get('x', 'GrLivArea')
    color_feature = request.args.get('color', 'OverallQual')
    
    data = train_df[[x_feature, 'SalePrice', color_feature]].dropna()
    if len(data) > 1000:
        data = data.sample(n=1000, random_state=42)
    
    hover_text = []
    for idx, row in data.iterrows():
        hover_text.append(
            f"{x_feature}: {row[x_feature]:,.0f}<br>" +
            f"Sale Price: ${row['SalePrice']:,.0f}<br>" +
            f"{color_feature}: {row[color_feature]}"
        )
    
    return jsonify({
        'x': data[x_feature].tolist(),
        'prices': data['SalePrice'].tolist(),
        'color_values': data[color_feature].tolist(),
        'hover_text': hover_text
    })

@app.route('/api/3d-scatter-data', methods=['GET'])
def get_3d_scatter_data():
    x_feature = request.args.get('x', 'GrLivArea')
    y_feature = request.args.get('y', 'OverallQual')
    
    data = train_df[[x_feature, y_feature, 'SalePrice']].dropna()
    if len(data) > 500:
        data = data.sample(n=500, random_state=42)
    
    hover_text = []
    for idx, row in data.iterrows():
        hover_text.append(
            f"{x_feature}: {row[x_feature]:,.0f}<br>" +
            f"{y_feature}: {row[y_feature]}<br>" +
            f"Sale Price: ${row['SalePrice']:,.0f}"
        )
    
    return jsonify({
        'x': data[x_feature].tolist(),
        'y': data[y_feature].tolist(),
        'prices': data['SalePrice'].tolist(),
        'hover_text': hover_text
    })

@app.route('/api/boxplot-data', methods=['GET'])
def get_boxplot_data():
    feature = request.args.get('feature', 'Neighborhood')
    top_categories = train_df[feature].value_counts().head(10).index
    filtered_data = train_df[train_df[feature].isin(top_categories)]
    
    data_list = []
    for category in top_categories:
        prices = filtered_data[filtered_data[feature] == category]['SalePrice'].tolist()
        data_list.append(prices)
    
    return jsonify({
        'data': data_list,
        'categories': top_categories.tolist(),
        'feature': feature
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, formatted_price, predicted_price,
                   formatted_lower, formatted_upper,
                   vs_average_diff, vs_average_percent,
                   input_features, actual_price, is_verified, user_rating
            FROM predictions 
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            try:
                # Parse input features
                features = {}
                if row[8]:
                    try:
                        features = json.loads(row[8])
                    except:
                        features = {}
                
                item = {
                    'id': row[0],
                    'timestamp': row[1],
                    'formatted_price': row[2],
                    'predicted_price': row[3],
                    'formatted_lower': row[4] if row[4] else 'N/A',
                    'formatted_upper': row[5] if row[5] else 'N/A',
                    'vs_average_diff': row[6] if row[6] else 'N/A',
                    'vs_average_percent': row[7] if row[7] else 'N/A',
                    'input_features': {
                        'GrLivArea': features.get('GrLivArea', 0),
                        'OverallQual': features.get('OverallQual', 0),
                        'YearBuilt': features.get('YearBuilt', 0),
                        'Neighborhood': features.get('Neighborhood', 'Unknown'),
                        'GarageCars': features.get('GarageCars', 0),
                        'TotalBsmtSF': features.get('TotalBsmtSF', 0),
                        'Fireplaces': features.get('Fireplaces', 0)
                    },
                    'actual_price': row[9] if len(row) > 9 else None,
                    'is_verified': bool(row[10]) if len(row) > 10 else False,
                    'user_rating': row[11] if len(row) > 11 else None
                }
                history.append(item)
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        print(f"Error in history endpoint: {e}")
        return jsonify({'success': True, 'history': []})

@app.route('/api/history/stats', methods=['GET'])
def get_history_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(predicted_price) FROM predictions')
        avg_result = cursor.fetchone()
        avg_prediction = avg_result[0] if avg_result[0] else 0
        
        cursor.execute('SELECT MIN(predicted_price), MAX(predicted_price) FROM predictions')
        min_max = cursor.fetchone()
        
        cursor.execute('SELECT COUNT(*) FROM predictions WHERE is_verified = 1')
        verified_predictions = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_predictions': total_predictions,
            'avg_prediction': float(avg_prediction),
            'min_prediction': float(min_max[0]) if min_max[0] else 0,
            'max_prediction': float(min_max[1]) if min_max[1] else 0,
            'verified_predictions': verified_predictions,
            'added_to_training': 0,
            'avg_rating': 0
        })
    except Exception as e:
        print(f"Error in history stats: {e}")
        return jsonify({
            'success': True,
            'total_predictions': 0,
            'avg_prediction': 0,
            'min_prediction': 0,
            'max_prediction': 0,
            'verified_predictions': 0,
            'added_to_training': 0,
            'avg_rating': 0
        })

@app.route('/api/history/clear', methods=['DELETE'])
def clear_history():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM predictions')
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'History cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/history/delete/<int:prediction_id>', methods=['DELETE'])
def delete_prediction(prediction_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM predictions WHERE id = ?', (prediction_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Prediction deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/predict', methods=['POST'])
def predict():
    prediction_id = None
    try:
        data = request.get_json()
        input_df = pd.DataFrame([data])

        required_features = feature_info['features']
        numeric_cols = feature_info['numeric_cols']
        categorical_cols = feature_info['categorical_cols']

        for col in required_features:
            if col not in input_df.columns:
                if col in numeric_cols:
                    input_df[col] = imputation_values['numeric_medians'].get(col, 0)
                else:
                    input_df[col] = imputation_values['categorical_modes'].get(col, 'None')

        input_df = input_df[required_features]

        for col in numeric_cols:
            if col in input_df.columns and pd.isnull(input_df[col]).any():
                input_df[col].fillna(imputation_values['numeric_medians'].get(col, 0), inplace=True)

        for col in categorical_cols:
            if col in input_df.columns and pd.isnull(input_df[col]).any():
                input_df[col].fillna(imputation_values['categorical_modes'].get(col, 'None'), inplace=True)

        X_numeric = input_df[numeric_cols].copy()
        X_encoded = X_numeric.copy()

        for col in categorical_cols:
            if col in input_df.columns:
                try:
                    X_encoded[col] = label_encoders[col].transform(input_df[col].astype(str))
                except:
                    X_encoded[col] = -1

        X_encoded = X_encoded[feature_info['all_features']]
        X_scaled = scaler.transform(X_encoded)
        prediction = model.predict(X_scaled)[0]

        confidence_lower = prediction * 0.9
        confidence_upper = prediction * 1.1
        
        formatted_price = f"${prediction:,.2f}"
        formatted_lower = f"${confidence_lower:,.2f}"
        formatted_upper = f"${confidence_upper:,.2f}"
        
        vs_average_diff = f"${prediction - mean_price:,.0f}"
        vs_average_percent = f"{((prediction - mean_price) / mean_price * 100):.1f}%"
        
        # Extract key features for display
        input_features = {
            'GrLivArea': data.get('GrLivArea', 0),
            'OverallQual': data.get('OverallQual', 0),
            'YearBuilt': data.get('YearBuilt', 0),
            'Neighborhood': data.get('Neighborhood', 'Unknown'),
            'GarageCars': data.get('GarageCars', 0),
            'TotalBsmtSF': data.get('TotalBsmtSF', 0),
            'Fireplaces': data.get('Fireplaces', 0)
        }
        
        # Save to database with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO predictions 
                    (timestamp, predicted_price, formatted_price, 
                     confidence_lower, confidence_upper, formatted_lower, formatted_upper,
                     input_features, all_features, vs_average_diff, vs_average_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    float(prediction),
                    formatted_price,
                    float(confidence_lower),
                    float(confidence_upper),
                    formatted_lower,
                    formatted_upper,
                    json.dumps(input_features),
                    json.dumps(data),
                    vs_average_diff,
                    vs_average_percent
                ))
                
                prediction_id = cursor.lastrowid
                conn.commit()
                conn.close()
                print(f"✅ Prediction saved with ID: {prediction_id}")
                break
                
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    print(f"Database locked, retrying... (attempt {attempt + 1})")
                    time.sleep(0.5)
                    continue
                else:
                    raise e
        
        return jsonify({
            'success': True,
            'predicted_price': round(prediction, 2),
            'formatted_price': formatted_price,
            'prediction_id': prediction_id,
            'confidence_range': {
                'lower': round(confidence_lower, 2),
                'upper': round(confidence_upper, 2),
                'formatted_lower': formatted_lower,
                'formatted_upper': formatted_upper
            },
            'vs_average': {
                'avg_price': f"${mean_price:,.0f}",
                'difference': vs_average_diff,
                'percent_diff': vs_average_percent
            }
        })

    except Exception as e:
        print("Error:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/feedback/<int:prediction_id>', methods=['POST'])
def add_feedback(prediction_id):
    try:
        data = request.get_json()
        actual_price = data.get('actual_price')
        user_rating = data.get('user_rating', 3)
        
        if not actual_price:
            return jsonify({'success': False, 'error': 'Actual price required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE predictions 
            SET actual_price = ?, is_verified = 1, user_rating = ?
            WHERE id = ?
        ''', (actual_price, user_rating, prediction_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Feedback recorded successfully!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/model-info', methods=['GET'])
def get_model_info():
    return jsonify({
        'success': True,
        'model_version': 1,
        'model_accuracy': 0.89,
        'total_samples': len(train_df),
        'user_samples': 0
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)