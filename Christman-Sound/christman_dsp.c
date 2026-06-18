// christman_dsp.c
// The Christman Bare-Metal Audio Engine
#include <math.h>
#include <stddef.h>

// Calculate RMS (Root Mean Square) Energy for Arousal/Dominance
void christman_rms(const float* audio, size_t length, float* out_rms) {
    if (length == 0) {
        *out_rms = 0.0f;
        return;
    }
    
    float sum = 0.0f;
    for (size_t i = 0; i < length; i++) {
        sum += audio[i] * audio[i];
    }
    *out_rms = sqrtf(sum / (float)length);
}

// Calculate Zero Crossing Rate for Valence Smoothness
void christman_zcr(const float* audio, size_t length, float* out_zcr) {
    if (length < 2) {
        *out_zcr = 0.0f;
        return;
    }

    size_t crossings = 0;
    for (size_t i = 1; i < length; i++) {
        // Detect if the wave crossed the zero line
        if ((audio[i] > 0.0f && audio[i - 1] <= 0.0f) || 
            (audio[i] <= 0.0f && audio[i - 1] > 0.0f)) {
            crossings++;
        }
    }
    *out_zcr = (float)crossings / (float)length;
}

#include <stdlib.h> // Required for malloc/free

// Bare-metal YIN Pitch Detection Algorithm
void christman_yin(const float* audio, size_t length, int sample_rate, float threshold, float* out_pitch) {
    int half_len = length / 2;
    if (half_len <= 0) {
        *out_pitch = 0.0f;
        return;
    }

    float* yin_buffer = (float*)malloc(half_len * sizeof(float));
    if (!yin_buffer) {
        *out_pitch = 0.0f;
        return;
    }

    // 1. Difference function
    for (int tau = 0; tau < half_len; tau++) {
        yin_buffer[tau] = 0.0f;
        for (int i = 0; i < half_len; i++) {
            float delta = audio[i] - audio[i + tau];
            yin_buffer[tau] += delta * delta;
        }
    }

    // 2. Cumulative mean normalized difference
    yin_buffer[0] = 1.0f;
    float running_sum = 0.0f;
    for (int tau = 1; tau < half_len; tau++) {
        running_sum += yin_buffer[tau];
        if (running_sum == 0.0f) {
            yin_buffer[tau] = 1.0f;
        } else {
            yin_buffer[tau] = yin_buffer[tau] * tau / running_sum;
        }
    }

    // 3. Absolute thresholding (find the period)
    int tau_estimate = -1;
    for (int tau = 2; tau < half_len; tau++) {
        if (yin_buffer[tau] < threshold) {
            // Found a dip, now find the local minimum
            while (tau + 1 < half_len && yin_buffer[tau + 1] < yin_buffer[tau]) {
                tau++;
            }
            tau_estimate = tau;
            break;
        }
    }

    // 4. Convert period to frequency
    if (tau_estimate != -1 && tau_estimate != 0) {
        *out_pitch = (float)sample_rate / (float)tau_estimate;
    } else {
        *out_pitch = 0.0f; // Unvoiced / No pitch detected
    }

    free(yin_buffer);
}

// Add this to christman_dsp.c

// Bare-metal Linear Predictive Coding (LPC) using Levinson-Durbin recursion
void christman_lpc(const float* audio, size_t length, int order, float* out_a) {
    if (length == 0 || order <= 0) {
        out_a[0] = 1.0f;
        for (int i = 1; i <= order; i++) out_a[i] = 0.0f;
        return;
    }

    // 1. Calculate Autocorrelation
    float* r = (float*)malloc((order + 1) * sizeof(float));
    if (!r) return;
    
    for (int lag = 0; lag <= order; lag++) {
        r[lag] = 0.0f;
        for (size_t i = 0; i < length - lag; i++) {
            r[lag] += audio[i] * audio[i + lag];
        }
    }

    // 2. Levinson-Durbin Recursion
    out_a[0] = 1.0f; // a[0] is always 1.0
    if (r[0] == 0.0f) {
        for (int i = 1; i <= order; i++) out_a[i] = 0.0f;
        free(r);
        return;
    }

    float error = r[0];
    float* k = (float*)malloc((order + 1) * sizeof(float));
    if (!k) { free(r); return; }

    for (int i = 1; i <= order; i++) {
        float sum = 0.0f;
        for (int j = 1; j < i; j++) {
            sum += out_a[j] * r[i - j];
        }
        k[i] = (r[i] - sum) / error;
        out_a[i] = k[i];

        // Update previous coefficients
        for (int j = 1; j <= i / 2; j++) {
            float temp = out_a[j] - k[i] * out_a[i - j];
            out_a[i - j] -= k[i] * out_a[j];
            out_a[j] = temp;
        }
        error *= (1.0f - k[i] * k[i]);
    }

    free(k);
    free(r);
}