from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import pandas as pd
import os
import sqlite3
import json
from datetime import datetime
import threading
import time
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# Database setup
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'predictions.db')
TRAINING_THRESHOLD = 3  # Retrain after every 3 verified predictions (for testing, you can increase to 10)

# Global variables for model management
current_model = None
current_scaler = None
current_label_encoders = None
current_feature_info = None
imputation_values = None
model_version = 1
is_training = False
original_training_samples = 0

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
original_training_samples = len(train_df)

print(f"📊 Original training data: {original_training_samples} samples")
print(f"📁 Model folder: {model_folder}")

# ==================== DATABASE INITIALIZATION ====================
def init_database():
    """Initialize SQLite database with predictions and training tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Main predictions table
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
    
    # Training data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            prediction_id INTEGER,
            features TEXT NOT NULL,
            actual_price REAL NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at TIMESTAMP,
            used_in_model INTEGER DEFAULT 0,
            model_version INTEGER
        )
    ''')
    
    # Model versions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            accuracy REAL,
            rmse REAL,
            mae REAL,
            trained_at TIMESTAMP,
            training_samples_original INTEGER,
            training_samples_user INTEGER,
            total_training_samples INTEGER,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Retraining log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS retraining_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            triggered_by TEXT,
            new_predictions INTEGER,
            previous_model_version INTEGER,
            new_model_version INTEGER,
            accuracy_improvement REAL,
            trained_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at: {DATABASE_PATH}")

# ==================== MODEL LOADING ====================
def load_initial_models():
    global current_model, current_scaler, current_label_encoders, current_feature_info, imputation_values, model_version
    
    try:
        current_model = joblib.load(model_path)
        current_scaler = joblib.load(scaler_path)
        current_label_encoders = joblib.load(encoders_path)
        imputation_values = joblib.load(imputation_path)
        current_feature_info = joblib.load(feature_info_path)
        print("✅ Initial model loaded successfully!")
        
        # Get latest model version from database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) FROM model_versions WHERE is_active = 1")
        result = cursor.fetchone()
        conn.close()
        
        if result[0] is None:
            save_initial_model_version()
        else:
            model_version = result[0]
            print(f"📌 Current model version: {model_version}")
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print("Please run model.py first to train the initial model")
        exit(1)

def save_initial_model_version():
    """Save initial model version info to database"""
    global model_version
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Calculate initial model performance
        X = train_df[current_feature_info['features']].copy()
        y = train_df['SalePrice']
        
        numeric_cols = current_feature_info['numeric_cols']
        categorical_cols = current_feature_info['categorical_cols']
        
        for col in numeric_cols:
            if col in X.columns:
                X[col].fillna(X[col].median(), inplace=True)
        
        for col in categorical_cols:
            if col in X.columns:
                X[col].fillna(X[col].mode()[0] if len(X[col].mode()) > 0 else 'Unknown', inplace=True)
        
        X_encoded = X[numeric_cols].copy()
        for col in categorical_cols:
            if col in X.columns and col in current_label_encoders:
                X_encoded[col] = current_label_encoders[col].transform(X[col].astype(str))
        
        X_scaled = current_scaler.transform(X_encoded[current_feature_info['all_features']])
        
        X_train, X_val, y_train, y_val = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        y_pred = current_model.predict(X_val)
        
        accuracy = r2_score(y_val, y_pred)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        mae = mean_absolute_error(y_val, y_pred)
        
        cursor.execute('''
            INSERT INTO model_versions 
            (version, accuracy, rmse, mae, trained_at, training_samples_original, 
             training_samples_user, total_training_samples, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (model_version, accuracy, rmse, mae, datetime.now().isoformat(), 
              original_training_samples, 0, original_training_samples))
        
        conn.commit()
        conn.close()
        print(f"✅ Initial model version {model_version} saved (R²: {accuracy:.4f})")
    except Exception as e:
        print(f"⚠️ Could not save initial model version: {e}")

# ==================== MODEL RETRAINING FUNCTION ====================
def retrain_with_all_data():
    """Retrain model using original data + all verified user predictions"""
    global is_training, current_model, current_scaler, current_label_encoders, model_version
    
    if is_training:
        print("⚠️ Training already in progress, skipping...")
        return
    
    is_training = True
    print("\n" + "="*60)
    print("🔄 STARTING MODEL RETRAINING")
    print("="*60)
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all verified predictions (both new and existing)
        cursor.execute('''
            SELECT id, all_features, actual_price
            FROM predictions 
            WHERE is_verified = 1 AND actual_price IS NOT NULL
            ORDER BY timestamp DESC
        ''')
        
        all_verified = cursor.fetchall()
        conn.close()
        
        if len(all_verified) == 0:
            print("⚠️ No verified predictions found. Skipping retraining.")
            is_training = False
            return
        
        # Separate new vs existing
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, all_features, actual_price
            FROM predictions 
            WHERE is_verified = 1 AND added_to_training = 0
        ''')
        new_predictions = cursor.fetchall()
        conn.close()
        
        print(f"📊 Found {len(new_predictions)} new verified predictions")
        print(f"📊 Total verified predictions: {len(all_verified)}")
        
        # Prepare original training data
        original_features = train_df[current_feature_info['features']].copy()
        original_prices = train_df['SalePrice']
        
        # Prepare all user prediction data
        all_user_features = []
        all_user_prices = []
        new_prediction_ids = []
        
        for pred in all_verified:
            pred_id, features_json, price = pred
            if features_json:
                try:
                    features = json.loads(features_json) if isinstance(features_json, str) else features_json
                    all_user_features.append(features)
                    all_user_prices.append(price)
                    # Check if this is a new prediction
                    is_new = False
                    for new_pred in new_predictions:
                        if new_pred[0] == pred_id:
                            is_new = True
                            break
                    if is_new:
                        new_prediction_ids.append(pred_id)
                except:
                    continue
        
        if len(all_user_features) == 0:
            print("⚠️ No valid user features found.")
            is_training = False
            return
        
        # Convert to DataFrame
        user_features_df = pd.DataFrame(all_user_features)
        
        # Combine datasets
        combined_features = pd.concat([original_features, user_features_df], ignore_index=True)
        combined_prices = pd.concat([original_prices, pd.Series(all_user_prices)], ignore_index=True)
        
        print(f"📈 Combined dataset: {len(original_features)} original + {len(all_user_features)} user = {len(combined_features)} samples")
        
        # Process features
        numeric_cols = current_feature_info['numeric_cols']
        categorical_cols = current_feature_info['categorical_cols']
        
        for col in numeric_cols:
            if col in combined_features.columns:
                combined_features[col].fillna(combined_features[col].median(), inplace=True)
        
        for col in categorical_cols:
            if col in combined_features.columns:
                mode_val = combined_features[col].mode()
                combined_features[col].fillna(mode_val[0] if len(mode_val) > 0 else 'Unknown', inplace=True)
        
        # Encode categorical variables
        X_encoded = combined_features[numeric_cols].copy()
        
        for col in categorical_cols:
            if col in combined_features.columns and col in current_label_encoders:
                X_encoded[col] = combined_features[col].astype(str).apply(
                    lambda x: current_label_encoders[col].transform([x])[0] 
                    if x in current_label_encoders[col].classes_ else -1
                )
        
        # Ensure all features are present
        for col in current_feature_info['all_features']:
            if col not in X_encoded.columns:
                X_encoded[col] = 0
        
        X_encoded = X_encoded[current_feature_info['all_features']]
        
        # Scale features
        X_scaled = current_scaler.fit_transform(X_encoded)
        
        # ===== FIX: Create a FIXED validation set using the ORIGINAL training data =====
        # Process original features the same way
        original_processed = original_features.copy()
        
        for col in numeric_cols:
            if col in original_processed.columns:
                original_processed[col].fillna(original_processed[col].median(), inplace=True)
        
        for col in categorical_cols:
            if col in original_processed.columns:
                mode_val = original_processed[col].mode()
                original_processed[col].fillna(mode_val[0] if len(mode_val) > 0 else 'Unknown', inplace=True)
        
        # Encode original features
        X_original_encoded = original_processed[numeric_cols].copy()
        
        for col in categorical_cols:
            if col in original_processed.columns and col in current_label_encoders:
                X_original_encoded[col] = current_label_encoders[col].transform(original_processed[col].astype(str))
        
        for col in current_feature_info['all_features']:
            if col not in X_original_encoded.columns:
                X_original_encoded[col] = 0
        
        X_original_encoded = X_original_encoded[current_feature_info['all_features']]
        X_original_scaled = current_scaler.transform(X_original_encoded)
        
        # Create a FIXED validation set from original data
        from sklearn.model_selection import train_test_split
        X_train_orig, X_val_fixed, y_train_orig, y_val_fixed = train_test_split(
            X_original_scaled, original_prices, test_size=0.2, random_state=42
        )
        
        print(f"📊 Fixed validation set size: {len(y_val_fixed)} houses")
        
        # Train new model on combined data
        new_model = Ridge(alpha=10.0)
        new_model.fit(X_scaled, combined_prices)
        
        # Evaluate OLD model on fixed validation set
        old_val_pred = current_model.predict(X_val_fixed)
        old_accuracy = r2_score(y_val_fixed, old_val_pred)
        old_rmse = np.sqrt(mean_squared_error(y_val_fixed, old_val_pred))
        old_mae = mean_absolute_error(y_val_fixed, old_val_pred)
        
        # Evaluate NEW model on fixed validation set
        # Need to transform validation data with new scaler
        # First, get the original validation features (before scaling)
        val_indices = y_val_fixed.index
        
        # Get the original validation features (unscaled, but processed)
        X_val_original = X_original_encoded.iloc[val_indices]
        
        # Transform with new scaler
        X_val_for_new = current_scaler.transform(X_val_original)
        new_val_pred = new_model.predict(X_val_for_new)
        new_accuracy = r2_score(y_val_fixed, new_val_pred)
        new_rmse = np.sqrt(mean_squared_error(y_val_fixed, new_val_pred))
        new_mae = mean_absolute_error(y_val_fixed, new_val_pred)
        
        print(f"\n📊 COMPARISON ON FIXED VALIDATION SET (292 original test houses):")
        print(f"🎯 New model accuracy: {new_accuracy:.4f}")
        print(f"📊 Current model accuracy: {old_accuracy:.4f}")
        print(f"📈 New model RMSE: ${new_rmse:,.2f}")
        print(f"📈 Current model RMSE: ${old_rmse:,.2f}")
        
        accuracy_improvement = new_accuracy - old_accuracy
        rmse_improvement = old_rmse - new_rmse
        
        # Update model if improved
        if new_accuracy > old_accuracy:
            print(f"\n✅ Model IMPROVED! Accuracy +{accuracy_improvement:.4f}")
            print(f"   RMSE -${rmse_improvement:,.2f}")
            
            # Update global model
            current_model = new_model
            
            # Create and fit new scaler with combined data
            new_scaler = StandardScaler()
            new_scaler.fit(X_encoded)
            current_scaler = new_scaler
            
            model_version += 1
            
            # Save new model files
            joblib.dump(current_model, model_path)
            joblib.dump(current_scaler, scaler_path)
            
            # Mark predictions as added to training
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            for pred_id in new_prediction_ids:
                cursor.execute("UPDATE predictions SET added_to_training = 1 WHERE id = ?", (pred_id,))
            
            # Save model version to database
            cursor.execute("UPDATE model_versions SET is_active = 0")
            cursor.execute('''
                INSERT INTO model_versions 
                (version, accuracy, rmse, mae, trained_at, 
                 training_samples_original, training_samples_user, total_training_samples, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', (model_version, new_accuracy, new_rmse, new_mae, datetime.now().isoformat(),
                  original_training_samples, len(all_user_features), len(combined_features)))
            
            # Log retraining
            cursor.execute('''
                INSERT INTO retraining_log 
                (triggered_by, new_predictions, previous_model_version, new_model_version, 
                 accuracy_improvement, trained_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('auto_retrain', len(new_predictions), model_version-1, model_version, 
                  accuracy_improvement, datetime.now().isoformat()))
            
            # Add to training_data table
            for idx, pred_id in enumerate(new_prediction_ids):
                # Find the feature data for this prediction
                pred_features = None
                for i, pred in enumerate(all_verified):
                    if pred[0] == pred_id:
                        pred_features = all_user_features[i]
                        break
                
                if pred_features:
                    cursor.execute('''
                        INSERT INTO training_data 
                        (source, prediction_id, features, actual_price, created_at, used_in_model, model_version)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', ('user_prediction', pred_id, json.dumps(pred_features), 
                          all_user_prices[i], datetime.now().isoformat(), 1, model_version))
            
            conn.commit()
            conn.close()
            
            print(f"\n🎉 Model updated to VERSION {model_version}!")
            print(f"   Total training samples: {len(combined_features)}")
            print(f"   User contributed samples: {len(all_user_features)}")
            
        else:
            print(f"\n⚠️ No improvement detected. Keeping current model (Version {model_version})")
            print(f"   Accuracy difference: {accuracy_improvement:.4f}")
            
            # Still mark as added to prevent reprocessing
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            for pred_id in new_prediction_ids:
                cursor.execute("UPDATE predictions SET added_to_training = 1 WHERE id = ?", (pred_id,))
            conn.commit()
            conn.close()
        
    except Exception as e:
        print(f"❌ Error during retraining: {e}")
        import traceback
        traceback.print_exc()
    finally:
        is_training = False
        print("="*60)
        print("✅ RETRAINING COMPLETED")
        print("="*60 + "\n")

        
def check_and_retrain():
    """Check if we have enough verified predictions and trigger retraining"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM predictions 
            WHERE is_verified = 1 AND added_to_training = 0
        ''')
        pending_count = cursor.fetchone()[0]
        conn.close()
        
        if pending_count >= TRAINING_THRESHOLD and not is_training:
            print(f"\n🔔 {pending_count} new verified predictions! Starting retraining...")
            threading.Thread(target=retrain_with_all_data).start()
            return True
        return False
    except Exception as e:
        print(f"Error checking retrain: {e}")
        return False

# ==================== API ENDPOINTS ====================
@app.route('/')
def home():
    return jsonify({
        'message': 'Ames House Price Prediction API with Active Learning',
        'model': 'Ridge Regression',
        'model_version': model_version,
        'training_samples': original_training_samples,
        'avg_price': f"${train_df['SalePrice'].mean():,.0f}"
    })

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    mean_price = train_df['SalePrice'].mean()
    median_price = train_df['SalePrice'].median()
    min_price = train_df['SalePrice'].min()
    max_price = train_df['SalePrice'].max()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM training_data WHERE source = 'user_prediction'")
    user_contributions = cursor.fetchone()[0]
    conn.close()
    
    return jsonify({
        'mean_price': float(mean_price),
        'median_price': float(median_price),
        'min_price': float(min_price),
        'max_price': float(max_price),
        'total_houses': len(train_df),
        'user_contributions': user_contributions,
        'model_version': model_version,
        'avg_living_area': float(train_df['GrLivArea'].mean()),
        'avg_lot_area': float(train_df['LotArea'].mean()),
        'avg_qual_rating': float(train_df['OverallQual'].mean()),
        'avg_garage_cars': float(train_df['GarageCars'].mean()),
        'avg_year_built': float(train_df['YearBuilt'].mean())
    })

@app.route('/api/model-info', methods=['GET'])
def get_model_info():
    """Get comprehensive model information"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT version, accuracy, rmse, mae, trained_at, 
               training_samples_original, training_samples_user, total_training_samples
        FROM model_versions WHERE is_active = 1
    ''')
    current = cursor.fetchone()
    
    cursor.execute('''
        SELECT COUNT(*) FROM predictions WHERE is_verified = 1 AND added_to_training = 0
    ''')
    pending_training = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM predictions WHERE is_verified = 1')
    total_verified = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'success': True,
        'model_version': current[0] if current else model_version,
        'model_accuracy': current[1] if current else 0.89,
        'model_rmse': current[2] if current else 0,
        'model_mae': current[3] if current else 0,
        'last_trained': current[4] if current else None,
        'original_samples': current[5] if current else original_training_samples,
        'user_samples': current[6] if current else 0,
        'total_samples': current[7] if current else original_training_samples,
        'pending_training': pending_training,
        'total_verified_predictions': total_verified,
        'retraining_threshold': TRAINING_THRESHOLD,
        'is_training': is_training
    })

@app.route('/api/feedback/<int:prediction_id>', methods=['POST'])
def add_feedback(prediction_id):
    """Add actual sale price feedback and trigger retraining"""
    try:
        data = request.get_json()
        actual_price = data.get('actual_price')
        user_rating = data.get('user_rating', 3)
        
        if not actual_price:
            return jsonify({'success': False, 'error': 'Actual price required'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE predictions 
            SET actual_price = ?, is_verified = 1, user_rating = ?
            WHERE id = ?
        ''', (actual_price, user_rating, prediction_id))
        
        conn.commit()
        conn.close()
        
        # Check and trigger retraining
        check_and_retrain()
        
        return jsonify({
            'success': True,
            'message': 'Feedback recorded! Model will improve with this data.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/force-retrain', methods=['POST'])
def force_retrain():
    """Manually trigger model retraining"""
    if is_training:
        return jsonify({'success': False, 'error': 'Training already in progress'}), 400
    
    threading.Thread(target=retrain_with_all_data).start()
    return jsonify({'success': True, 'message': 'Retraining started in background'})

@app.route('/api/training-status', methods=['GET'])
def get_training_status():
    return jsonify({
        'is_training': is_training,
        'threshold': TRAINING_THRESHOLD,
        'model_version': model_version
    })

# ==================== CHART DATA ENDPOINTS ====================
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
    coefficients = current_model.coef_
    feature_names = current_feature_info['all_features']
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

# ==================== HISTORY ENDPOINTS ====================
@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
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
                continue
        
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': True, 'history': []})

@app.route('/api/history/stats', methods=['GET'])
def get_history_stats():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(predicted_price) FROM predictions')
        avg_prediction = cursor.fetchone()[0] or 0
        
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
            'verified_predictions': verified_predictions
        })
    except Exception as e:
        return jsonify({'success': True, 'total_predictions': 0})

@app.route('/api/history/clear', methods=['DELETE'])
def clear_history():
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
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM predictions WHERE id = ?', (prediction_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Prediction deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ==================== PREDICTION ENDPOINT ====================
@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        input_df = pd.DataFrame([data])

        required_features = current_feature_info['features']
        numeric_cols = current_feature_info['numeric_cols']
        categorical_cols = current_feature_info['categorical_cols']

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
                    X_encoded[col] = current_label_encoders[col].transform(input_df[col].astype(str))
                except:
                    X_encoded[col] = -1

        X_encoded = X_encoded[current_feature_info['all_features']]
        X_scaled = current_scaler.transform(X_encoded)
        prediction = current_model.predict(X_scaled)[0]

        confidence_lower = prediction * 0.9
        confidence_upper = prediction * 1.1
        
        formatted_price = f"${prediction:,.2f}"
        formatted_lower = f"${confidence_lower:,.2f}"
        formatted_upper = f"${confidence_upper:,.2f}"
        
        mean_price = train_df['SalePrice'].mean()
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
        
        # Save to database
        try:
            conn = sqlite3.connect(DATABASE_PATH)
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
            
        except Exception as db_error:
            print(f"⚠️ Database error: {db_error}")

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
        return jsonify({'success': False, 'error': str(e)}), 400

# ==================== INITIALIZATION ====================
if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Load models
    load_initial_models()
    
    # Calculate statistics for display
    mean_price = train_df['SalePrice'].mean()
    
    print("\n" + "="*60)
    print("🚀 AMES HOUSE PRICE PREDICTOR API")
    print("="*60)
    print(f"📊 Model Version: {model_version}")
    print(f"📈 Training Samples: {original_training_samples}")
    print(f"💰 Average Price: ${mean_price:,.2f}")
    print(f"🔄 Auto-retrain threshold: {TRAINING_THRESHOLD} verified predictions")
    print("="*60)
    print("\n✅ Server is running on http://localhost:5000")
    print("💡 Tip: Add actual sale prices to improve the model!\n")
    
    app.run(debug=True, port=5000)