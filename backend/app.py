from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import pandas as pd
import os
import sqlite3
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# Database setup
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'predictions.db')

def init_database():
    """Initialize SQLite database with predictions table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            predicted_price REAL NOT NULL,
            formatted_price TEXT NOT NULL,
            confidence_lower REAL NOT NULL,
            confidence_upper REAL NOT NULL,
            formatted_lower TEXT NOT NULL,
            formatted_upper TEXT NOT NULL,
            input_features TEXT NOT NULL,
            vs_average_diff TEXT,
            vs_average_percent TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at: {DATABASE_PATH}")

# Call database initialization
init_database()

# Get the absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Model paths
model_folder = os.path.join(project_root, 'model')
if not os.path.exists(model_folder):
    model_folder = os.path.join(project_root, 'models')

model_path = os.path.join(model_folder, 'ridge_model.pkl')
scaler_path = os.path.join(model_folder, 'scaler.pkl')
encoders_path = os.path.join(model_folder, 'label_encoders.pkl')
imputation_path = os.path.join(model_folder, 'imputation_values.pkl')
feature_info_path = os.path.join(model_folder, 'feature_info.pkl')

# Load training data
train_data_path = os.path.join(current_dir, 'data', 'train.csv')
train_df = pd.read_csv(train_data_path)

print(f"Project root: {project_root}")
print(f"Model folder: {model_folder}")
print(f"Train data path: {train_data_path}")

# Load models
try:
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    label_encoders = joblib.load(encoders_path)
    imputation_values = joblib.load(imputation_path)
    feature_info = joblib.load(feature_info_path)
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    print(f"Please ensure model files exist in: {model_folder}")

# Calculate statistics
mean_price = train_df['SalePrice'].mean()
median_price = train_df['SalePrice'].median()
std_price = train_df['SalePrice'].std()
min_price = train_df['SalePrice'].min()
max_price = train_df['SalePrice'].max()

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
    """Get basic statistics about the dataset"""
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
    """Get price distribution data for histogram"""
    prices = train_df['SalePrice'].tolist()
    return jsonify({'prices': prices})

@app.route('/api/correlation-matrix', methods=['GET'])
def get_correlation_matrix():
    """Get full correlation matrix for all numeric features"""
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
    """Get correlation with SalePrice for key features"""
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
    """Get feature importance based on model coefficients"""
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
    """Get average price by neighborhood"""
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
    """Get average price by year built"""
    yearly_stats = train_df.groupby('YearBuilt')['SalePrice'].agg(['mean', 'median', 'count']).reset_index()

    return jsonify({
        'years': yearly_stats['YearBuilt'].tolist(),
        'means': yearly_stats['mean'].tolist(),
        'medians': yearly_stats['median'].tolist(),
        'counts': yearly_stats['count'].tolist()
    })

@app.route('/api/price-by-quality', methods=['GET'])
def get_price_by_quality():
    """Get price distribution by overall quality"""
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
    """Get data for 2D scatter plots with color encoding"""
    x_feature = request.args.get('x', 'GrLivArea')
    color_feature = request.args.get('color', 'OverallQual')
    
    if x_feature not in train_df.columns:
        return jsonify({'error': f'Feature {x_feature} not found'}), 400
    
    if color_feature not in train_df.columns:
        return jsonify({'error': f'Feature {color_feature} not found'}), 400
    
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
        'hover_text': hover_text,
        'x_feature': x_feature,
        'color_feature': color_feature
    })

@app.route('/api/3d-scatter-data', methods=['GET'])
def get_3d_scatter_data():
    """Get data for 3D scatter plot (X, Y axes, Z = SalePrice)"""
    x_feature = request.args.get('x', 'GrLivArea')
    y_feature = request.args.get('y', 'OverallQual')
    
    if x_feature not in train_df.columns:
        return jsonify({'error': f'Feature {x_feature} not found'}), 400
    
    if y_feature not in train_df.columns:
        return jsonify({'error': f'Feature {y_feature} not found'}), 400
    
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
        'hover_text': hover_text,
        'x_feature': x_feature,
        'y_feature': y_feature
    })

@app.route('/api/boxplot-data', methods=['GET'])
def get_boxplot_data():
    """Get data for box plots by category"""
    feature = request.args.get('feature', 'Neighborhood')

    if feature not in train_df.columns:
        return jsonify({'error': 'Feature not found'}), 400

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
    """Get all prediction history from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # FIXED: Added formatted_lower and formatted_upper to SELECT query
        cursor.execute('''
            SELECT id, timestamp, formatted_price, predicted_price,
                   confidence_lower, confidence_upper, 
                   formatted_lower, formatted_upper,
                   input_features, vs_average_diff, vs_average_percent
            FROM predictions 
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'id': row[0],
                'timestamp': row[1],
                'formatted_price': row[2],
                'predicted_price': row[3],
                'confidence_lower': row[4],
                'confidence_upper': row[5],
                'formatted_lower': row[6],      # Added
                'formatted_upper': row[7],      # Added
                'input_features': json.loads(row[8]),
                'vs_average_diff': row[9],
                'vs_average_percent': row[10]
            })
        
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/history/clear', methods=['DELETE'])
def clear_history():
    """Clear all prediction history"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM predictions')
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'History cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/history/delete/<int:prediction_id>', methods=['DELETE'])
def delete_prediction(prediction_id):
    """Delete a single prediction from history"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM predictions WHERE id = ?', (prediction_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Prediction deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/history/stats', methods=['GET'])
def get_history_stats():
    """Get statistics about prediction history"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(predicted_price) FROM predictions')
        avg_prediction = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT MIN(predicted_price), MAX(predicted_price) FROM predictions')
        min_max = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_predictions': total_predictions,
            'avg_prediction': float(avg_prediction),
            'min_prediction': float(min_max[0]) if min_max[0] else 0,
            'max_prediction': float(min_max[1]) if min_max[1] else 0
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/predict', methods=['POST'])
def predict():
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
        
        # Save to database
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Extract key features for storage (limit to important ones)
            important_features = {
                'GrLivArea': data.get('GrLivArea', 0),
                'OverallQual': data.get('OverallQual', 0),
                'YearBuilt': data.get('YearBuilt', 0),
                'Neighborhood': data.get('Neighborhood', 'Unknown'),
                'GarageCars': data.get('GarageCars', 0),
                'TotalBsmtSF': data.get('TotalBsmtSF', 0),
                'Fireplaces': data.get('Fireplaces', 0)
            }
            
            cursor.execute('''
                INSERT INTO predictions 
                (timestamp, predicted_price, formatted_price, confidence_lower, confidence_upper,
                 formatted_lower, formatted_upper, input_features, vs_average_diff, vs_average_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                float(prediction),
                formatted_price,
                float(confidence_lower),
                float(confidence_upper),
                formatted_lower,
                formatted_upper,
                json.dumps(important_features),
                vs_average_diff,
                vs_average_percent
            ))
            
            conn.commit()
            conn.close()
            print("✅ Prediction saved to database")
        except Exception as db_error:
            print(f"⚠️ Database error: {db_error}")

        return jsonify({
            'success': True,
            'predicted_price': round(prediction, 2),
            'formatted_price': formatted_price,
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
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)