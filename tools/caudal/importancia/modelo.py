#!/usr/bin/env python3
"""
Caudal · Importancia — regresión logística en stdlib puro.

Sin numpy ni sklearn a propósito: el scoring corre dentro de la Lambda
`caudal-analiza`, que se empaqueta como stdlib + boto3. Con ~10k filas y ~35
features el descenso de gradiente es instantáneo, así que el entrenamiento usa
el mismo código y no hay dos implementaciones que puedan desalinearse.

Se eligió logística y no un árbol/bosque por tres razones, en orden:
  1. los pesos se leen — `explicacion()` puede decir qué inclinó la balanza y
     eso es exactamente el hueco que reportó el motor de alertas;
  2. calibra en probabilidad, y el eje de riesgo la necesita como probabilidad
     de verdad (impacto × P) y no como un ranking;
  3. se serializa a un JSON de 3 KB que la Lambda lee sin dependencias.
"""
import json
import math
import random


def sigmoide(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)                      # evita overflow con z muy negativo
    return e / (1.0 + e)


class Logistica:
    def __init__(self, nombres):
        self.nombres = list(nombres)
        self.w = [0.0] * len(nombres)
        self.b = 0.0
        self.mu = [0.0] * len(nombres)
        self.sd = [1.0] * len(nombres)
        self.meta = {}

    # -- entrenamiento ----------------------------------------------------
    def fit(self, X, y, epocas=400, lr=0.35, l2=1e-3, semilla=7, verbose=False):
        n, d = len(X), len(self.nombres)
        assert n and len(X[0]) == d

        # estandarizar: sin esto, features con prevalencias muy distintas
        # (gobierno 10% vs firmas_1 50%) avanzan a velocidades distintas y el
        # lr único no le sirve a ninguna.
        for j in range(d):
            col = [X[i][j] for i in range(n)]
            m = sum(col) / n
            var = sum((c - m) ** 2 for c in col) / n
            self.mu[j] = m
            self.sd[j] = math.sqrt(var) if var > 1e-12 else 1.0

        Z = [[(X[i][j] - self.mu[j]) / self.sd[j] for j in range(d)]
             for i in range(n)]

        base = sum(y) / n
        self.b = math.log(base / (1 - base)) if 0 < base < 1 else 0.0
        self.w = [0.0] * d
        vel = [0.0] * d
        vb = 0.0
        mom = 0.9
        rnd = random.Random(semilla)
        idx = list(range(n))

        for ep in range(epocas):
            rnd.shuffle(idx)
            gw = [0.0] * d
            gb = 0.0
            for i in idx:
                zi = Z[i]
                p = sigmoide(sum(self.w[j] * zi[j] for j in range(d)) + self.b)
                err = p - y[i]
                for j in range(d):
                    if zi[j]:
                        gw[j] += err * zi[j]
                gb += err
            for j in range(d):
                g = gw[j] / n + l2 * self.w[j]
                vel[j] = mom * vel[j] - lr * g
                self.w[j] += vel[j]
            vb = mom * vb - lr * (gb / n)
            self.b += vb
            if verbose and ep % 100 == 0:
                print(f'    ep {ep:3d}  logloss={self.logloss(X, y):.4f}')
        return self

    # -- inferencia -------------------------------------------------------
    def prob(self, x):
        z = self.b
        for j, wj in enumerate(self.w):
            if x[j]:
                z += wj * (x[j] - self.mu[j]) / self.sd[j]
            else:
                z += wj * (0.0 - self.mu[j]) / self.sd[j]
        return sigmoide(z)

    def probs(self, X):
        return [self.prob(x) for x in X]

    def pesos_crudos(self):
        """Peso en la escala original (para explicacion(): x=1 vs x=0)."""
        return [self.w[j] / self.sd[j] for j in range(len(self.w))]

    # -- métricas ---------------------------------------------------------
    def logloss(self, X, y):
        p = self.probs(X)
        eps = 1e-12
        return -sum(y[i] * math.log(max(p[i], eps))
                    + (1 - y[i]) * math.log(max(1 - p[i], eps))
                    for i in range(len(y))) / len(y)

    # -- serialización ----------------------------------------------------
    def a_dict(self):
        return {'features': self.nombres, 'w': [round(v, 6) for v in self.w],
                'b': round(self.b, 6), 'mu': [round(v, 6) for v in self.mu],
                'sd': [round(v, 6) for v in self.sd], 'meta': self.meta}

    @classmethod
    def de_dict(cls, d):
        m = cls(d['features'])
        m.w, m.b, m.mu, m.sd = d['w'], d['b'], d['mu'], d['sd']
        m.meta = d.get('meta', {})
        return m

    def guardar(self, path):
        with open(path, 'w') as fh:
            json.dump(self.a_dict(), fh, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# métricas de evaluación
# ---------------------------------------------------------------------------
def auc(y, p):
    """AUC-ROC por rangos (Mann-Whitney U), con empates promediados."""
    pares = sorted(zip(p, y))
    rangos = [0.0] * len(pares)
    i = 0
    while i < len(pares):
        j = i
        while j + 1 < len(pares) and pares[j + 1][0] == pares[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            rangos[k] = r
        i = j + 1
    npos = sum(yy for _, yy in pares)
    nneg = len(pares) - npos
    if not npos or not nneg:
        return float('nan')
    spos = sum(rangos[k] for k in range(len(pares)) if pares[k][1] == 1)
    return (spos - npos * (npos + 1) / 2.0) / (npos * nneg)


def brier(y, p):
    return sum((p[i] - y[i]) ** 2 for i in range(len(y))) / len(y)


def calibracion(y, p, k=10):
    """Tabla decil: predicho vs observado. Un AUC alto con calibración torcida
    ordena bien pero miente en la cifra, y el eje de riesgo multiplica por esa
    cifra."""
    orden = sorted(range(len(p)), key=lambda i: p[i])
    out = []
    n = len(orden)
    for d in range(k):
        lo, hi = d * n // k, (d + 1) * n // k
        gr = orden[lo:hi]
        if not gr:
            continue
        out.append({'decil': d + 1, 'n': len(gr),
                    'p_medio': round(sum(p[i] for i in gr) / len(gr), 4),
                    'obs': round(sum(y[i] for i in gr) / len(gr), 4)})
    return out


def lift(y, p, frac=0.1):
    """Cuántas veces más leyes hay en el top `frac` que en la base."""
    n = len(y)
    k = max(1, int(n * frac))
    top = sorted(range(n), key=lambda i: -p[i])[:k]
    tasa_top = sum(y[i] for i in top) / k
    base = sum(y) / n
    return {'n_top': k, 'tasa_top': round(tasa_top, 4),
            'tasa_base': round(base, 4),
            'lift': round(tasa_top / base, 2) if base else None}
