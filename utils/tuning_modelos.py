"""
tuning_modelos.py — Tuning de hiperparámetros con RandomizedSearchCV

Compara 4 modelos de ensamble con búsqueda aleatoria de hiperparámetros:
    1. LightGBM
    2. XGBoost
    3. Random Forest
    4. HistGradientBoostingRegressor

Cada modelo se evalúa con CV k-fold usando R² y RMSE.
El ganador, según mayor R² promedio, pasa a SHAP para el análisis
de interpretabilidad del Notebook 2.

Uso típico desde notebook:
    from tuning_modelos import tunear_todos
    resultados = tunear_todos(X, y, n_iter=20, cv=5, n_jobs=-1)
    mejor_modelo = resultados['modelo_ganador']
"""

import time
import numpy as np
import pandas as pd

from scipy.stats import randint, uniform

from sklearn.base import clone
from sklearn.model_selection import RandomizedSearchCV, KFold, cross_val_score
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

import lightgbm as lgb
import xgboost as xgb


# ============================================================================
# UTILIDADES
# ============================================================================

def limpiar_params(params):
    """
    Convierte tipos NumPy como np.float64 / np.int64 a tipos nativos de Python.
    Esto ayuda a evitar errores de clonación con algunos modelos.
    """
    params_limpios = {}

    for k, v in params.items():
        if isinstance(v, np.integer):
            params_limpios[k] = int(v)
        elif isinstance(v, np.floating):
            params_limpios[k] = float(v)
        else:
            params_limpios[k] = v

    return params_limpios


# ============================================================================
# ESPACIOS DE BÚSQUEDA
# ============================================================================
# Espacios compactos porque el dataset distrital tiene aprox. 1,874 observaciones.
# No conviene hacer un tuning demasiado grande para una entrega de concurso.

PARAM_LGB = {
    'n_estimators':      randint(150, 500),
    'max_depth':         randint(3, 8),
    'learning_rate':     uniform(0.01, 0.09),
    'num_leaves':        randint(15, 70),
    'min_child_samples': randint(10, 50),
    'reg_alpha':         uniform(0, 1),
    'reg_lambda':        uniform(0, 1),
    'subsample':         uniform(0.7, 0.3),
    'colsample_bytree':  uniform(0.7, 0.3),
}

PARAM_XGB = {
    'n_estimators':     randint(150, 500),
    'max_depth':        randint(3, 8),
    'learning_rate':    uniform(0.01, 0.09),
    'min_child_weight': randint(1, 10),
    'reg_alpha':        uniform(0, 1),
    'reg_lambda':       uniform(0, 1),
    'subsample':        uniform(0.7, 0.3),
    'colsample_bytree': uniform(0.7, 0.3),
}

PARAM_RF = {
    'n_estimators':      randint(200, 500),
    'max_depth':         randint(5, 25),
    'min_samples_split': randint(2, 20),
    'min_samples_leaf':  randint(1, 15),
    'max_features':      uniform(0.5, 0.5),
}

PARAM_HGB = {
    'max_iter':          randint(100, 400),
    'learning_rate':     uniform(0.01, 0.12),
    'max_leaf_nodes':    randint(15, 60),
    'max_depth':         randint(3, 10),
    'min_samples_leaf':  randint(10, 50),
    'l2_regularization': uniform(0.0, 1.0),
}


# ============================================================================
# TUNER GENÉRICO
# ============================================================================

def tunear_modelo(
    nombre,
    base_estimator,
    param_dist,
    X,
    y,
    n_iter=20,
    cv=5,
    n_jobs=-1,
    random_state=42,
    verbose=False
):
    """
    Aplica RandomizedSearchCV a un modelo y devuelve un diccionario con métricas.

    Métricas:
        - best_r2: R² promedio del mejor modelo en CV
        - rmse_mean: RMSE promedio usando CV manual sobre el mejor estimador
        - rmse_std: desviación estándar del RMSE
    """
    print(f"\n  → Tuneando {nombre}... ", end='', flush=True)
    t0 = time.time()

    kf = KFold(
        n_splits=cv,
        shuffle=True,
        random_state=random_state
    )

    search = RandomizedSearchCV(
        estimator=base_estimator,
        param_distributions=param_dist,
        n_iter=n_iter,
        cv=kf,
        scoring='r2',
        n_jobs=n_jobs,
        random_state=random_state,
        verbose=1 if verbose else 0,
        return_train_score=False,
    )

    search.fit(X, y)

    # Limpiamos parámetros para evitar problemas con tipos np.float64 / np.int64
    best_params = limpiar_params(search.best_params_)

    # Reconstruimos el mejor estimador de forma segura
    best_estimator = clone(base_estimator).set_params(**best_params)

    # Calculamos RMSE con validación cruzada sobre el mejor estimador
    rmse_scores = -cross_val_score(
        best_estimator,
        X,
        y,
        cv=kf,
        scoring='neg_root_mean_squared_error',
        n_jobs=n_jobs
    )

    # Entrenamos el modelo final con todo el dataset
    best_estimator.fit(X, y)

    elapsed = time.time() - t0
    print(f'OK ({elapsed:.1f}s)')

    return {
        'nombre':         nombre,
        'best_r2':        search.best_score_,
        'rmse_mean':      rmse_scores.mean(),
        'rmse_std':       rmse_scores.std(),
        'best_params':    best_params,
        'best_estimator': best_estimator,
        'cv_results':     search.cv_results_,
        'tiempo_s':       elapsed,
    }


# ============================================================================
# PIPELINE COMPLETO: 4 MODELOS
# ============================================================================

def tunear_todos(
    X,
    y,
    n_iter=20,
    cv=5,
    n_jobs=-1,
    random_state=42,
    verbose=False
):
    """
    Tunea LightGBM, XGBoost, Random Forest e HistGradientBoosting.

    Devuelve:
        - resultados: lista de dicts, uno por modelo
        - comparacion: DataFrame ordenado por R² descendente
        - modelo_ganador: mejor estimador entrenado con todo X, y
        - nombre_ganador: nombre del modelo ganador
        - best_params: mejores hiperparámetros del ganador
    """
    print(f"{'=' * 65}")
    print(f"TUNING DE 4 MODELOS — n_iter={n_iter} por modelo, cv={cv}-fold")
    print(f"X: {X.shape}, y: {y.shape}")
    print(f"{'=' * 65}")

    resultados = []

    # ------------------------------------------------------------------------
    # 1. LightGBM
    # ------------------------------------------------------------------------
    resultados.append(tunear_modelo(
        nombre='LightGBM',
        base_estimator=lgb.LGBMRegressor(
            random_state=random_state,
            verbose=-1,
            n_jobs=1
        ),
        param_dist=PARAM_LGB,
        X=X,
        y=y,
        n_iter=n_iter,
        cv=cv,
        n_jobs=n_jobs,
        random_state=random_state,
        verbose=verbose
    ))

    # ------------------------------------------------------------------------
    # 2. XGBoost
    # ------------------------------------------------------------------------
    resultados.append(tunear_modelo(
        nombre='XGBoost',
        base_estimator=xgb.XGBRegressor(
            random_state=random_state,
            objective='reg:squarederror',
            eval_metric='rmse',
            verbosity=0,
            n_jobs=1
        ),
        param_dist=PARAM_XGB,
        X=X,
        y=y,
        n_iter=n_iter,
        cv=cv,
        n_jobs=n_jobs,
        random_state=random_state,
        verbose=verbose
    ))

    # ------------------------------------------------------------------------
    # 3. Random Forest
    # ------------------------------------------------------------------------
    resultados.append(tunear_modelo(
        nombre='RandomForest',
        base_estimator=RandomForestRegressor(
            random_state=random_state,
            n_jobs=1
        ),
        param_dist=PARAM_RF,
        X=X,
        y=y,
        n_iter=n_iter,
        cv=cv,
        n_jobs=n_jobs,
        random_state=random_state,
        verbose=verbose
    ))

    # ------------------------------------------------------------------------
    # 4. HistGradientBoosting
    # ------------------------------------------------------------------------
    resultados.append(tunear_modelo(
        nombre='HistGradientBoosting',
        base_estimator=HistGradientBoostingRegressor(
            random_state=random_state,
            early_stopping=True
        ),
        param_dist=PARAM_HGB,
        X=X,
        y=y,
        n_iter=n_iter,
        cv=cv,
        n_jobs=n_jobs,
        random_state=random_state,
        verbose=verbose
    ))

    # ------------------------------------------------------------------------
    # Tabla comparativa
    # ------------------------------------------------------------------------
    comparacion = pd.DataFrame([
        {
            'modelo':    r['nombre'],
            'R²_mean':   r['best_r2'],
            'RMSE_mean': r['rmse_mean'],
            'RMSE_std':  r['rmse_std'],
            'tiempo_s':  r['tiempo_s'],
        }
        for r in resultados
    ])

    comparacion = (
        comparacion
        .sort_values('R²_mean', ascending=False)
        .round(3)
        .reset_index(drop=True)
    )

    # ------------------------------------------------------------------------
    # Ganador
    # ------------------------------------------------------------------------
    idx_ganador = max(
        range(len(resultados)),
        key=lambda i: resultados[i]['best_r2']
    )

    ganador = resultados[idx_ganador]

    print(f"\n{'=' * 65}")
    print("RESULTADOS ORDENADOS POR R²")
    print(f"{'=' * 65}")
    print(comparacion.to_string(index=False))

    print(f"\n→ Ganador: {ganador['nombre']} (R² = {ganador['best_r2']:.3f})")

    print("\nMejores hiperparámetros del ganador:")
    for k, v in ganador['best_params'].items():
        if isinstance(v, float):
            print(f"  {k:22s} = {v:.4f}")
        else:
            print(f"  {k:22s} = {v}")

    return {
        'resultados':     resultados,
        'comparacion':    comparacion,
        'modelo_ganador': ganador['best_estimator'],
        'nombre_ganador': ganador['nombre'],
        'best_params':    ganador['best_params'],
    }