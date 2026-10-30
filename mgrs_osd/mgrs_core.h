/*
 * mgrs_core.h - WGS84 lat/long to MGRS, plain C, no allocation.
 * Shared by the ArduPilot (AP_OSD) and Betaflight (osd_elements.c) patches.
 *
 * Output example: "18S UJ 2339 0739"  (zone is always two digits, e.g. 02D)
 *
 * mgrs_format(lat_e7, lon_e7, digits, buf, len)
 *   lat_e7/lon_e7: degrees * 1e7 (the integer format both firmwares use)
 *   digits: 1..5 per axis (5 = 1 m, 4 = 10 m, 3 = 100 m)
 *   returns 1 on success, 0 if outside 80S..84N (polar, not handled)
 *
 * Transverse Mercator: Karney / Kruger series, 6th order.
 */
#pragma once

#include <math.h>
#include <stddef.h>
#include <stdint.h>

#ifndef MGRS_DIGITS
#define MGRS_DIGITS 4
#endif

#ifdef __cplusplus
extern "C" {
#endif

static inline int mgrs_format(int32_t lat_e7, int32_t lon_e7, int digits, char *buf, size_t len)
{
    static const char BAND[] = "CDEFGHJKLMNPQRSTUVWX";
    static const char COL[]  = "ABCDEFGHJKLMNPQRSTUVWXYZ";
    static const char ROW[]  = "ABCDEFGHJKLMNPQRSTUV";

    const double lat = lat_e7 * 1e-7;
    const double lon = lon_e7 * 1e-7;
    if (lat >= 84.0 || lat < -80.0) {
        return 0;
    }
    if (digits < 1) { digits = 1; }
    if (digits > 5) { digits = 5; }

    const double A = 6378137.0;
    const double F = 1.0 / 298.257223563;
    const double K0 = 0.9996;
    const double n = F / (2.0 - F);
    const double n2 = n * n, n3 = n2 * n, n4 = n2 * n2, n5 = n4 * n, n6 = n3 * n3;
    const double BIG_A = A / (1.0 + n) * (1.0 + n2 / 4.0 + n4 / 64.0 + n6 / 256.0);
    const double alpha[6] = {
        n / 2 - 2 * n2 / 3 + 5 * n3 / 16 + 41 * n4 / 180 - 127 * n5 / 288 + 7891 * n6 / 37800,
        13 * n2 / 48 - 3 * n3 / 5 + 557 * n4 / 1440 + 281 * n5 / 630 - 1983433 * n6 / 1935360,
        61 * n3 / 240 - 103 * n4 / 140 + 15061 * n5 / 26880 + 167603 * n6 / 181440,
        49561 * n4 / 161280 - 179 * n5 / 168 + 6601661 * n6 / 7257600,
        34729 * n5 / 80640 - 3418889 * n6 / 1995840,
        212378941 * n6 / 319334400,
    };

    /* UTM zone, with the Norway and Svalbard exceptions */
    int zone = (int)floor((lon + 180.0) / 6.0) + 1;
    if (zone > 60) { zone = 60; }
    if (lat >= 56 && lat < 64 && lon >= 3 && lon < 12) {
        zone = 32;
    } else if (lat >= 72 && lat < 84) {
        if (lon >= 0 && lon < 9)        { zone = 31; }
        else if (lon >= 9 && lon < 21)  { zone = 33; }
        else if (lon >= 21 && lon < 33) { zone = 35; }
        else if (lon >= 33 && lon < 42) { zone = 37; }
    }

    const double lon0 = (zone - 1) * 6.0 - 180.0 + 3.0;
    const double DEG2RAD = 3.14159265358979323846 / 180.0;
    const double phi = lat * DEG2RAD;
    const double lam = (lon - lon0) * DEG2RAD;
    const double c = 2.0 * sqrt(n) / (1.0 + n);
    const double sphi = sin(phi);
    const double t = sinh(atanh(sphi) - c * atanh(c * sphi));
    const double xi0 = atan2(t, cos(lam));
    const double eta0 = atanh(sin(lam) / sqrt(1.0 + t * t));
    double xi = xi0, eta = eta0;
    for (int j = 1; j <= 6; j++) {
        xi  += alpha[j - 1] * sin(2 * j * xi0) * cosh(2 * j * eta0);
        eta += alpha[j - 1] * cos(2 * j * xi0) * sinh(2 * j * eta0);
    }
    double e = 500000.0 + K0 * BIG_A * eta;
    double nn = K0 * BIG_A * xi;
    if (lat < 0) { nn += 10000000.0; }

    int band = (int)floor((lat + 80.0) / 8.0);
    if (band > 19) { band = 19; }
    const int set = (zone - 1) % 3;
    const int col = (int)floor(e / 100000.0);
    const int row = ((int)floor(nn / 100000.0) + ((zone % 2 == 0) ? 5 : 0)) % 20;
    if (col < 1 || col > 8) {
        return 0;
    }

    long ei = (long)floor(e) % 100000;
    long ni = (long)floor(nn) % 100000;
    long div = 1;
    for (int i = digits; i < 5; i++) { div *= 10; }
    ei /= div;
    ni /= div;

    /* hand-formatted so no printf is needed: "ZZB CC EEEE NNNN" */
    if (len < (size_t)(2 * digits + 8)) {
        return 0;
    }
    char *p = buf;
    *p++ = (char)('0' + zone / 10);
    *p++ = (char)('0' + zone % 10);
    *p++ = BAND[band];
    *p++ = ' ';
    *p++ = COL[set * 8 + col - 1];
    *p++ = ROW[row];
    *p++ = ' ';
    for (int i = digits - 1; i >= 0; i--) {
        long d = 1;
        for (int k = 0; k < i; k++) { d *= 10; }
        *p++ = (char)('0' + (ei / d) % 10);
    }
    *p++ = ' ';
    for (int i = digits - 1; i >= 0; i--) {
        long d = 1;
        for (int k = 0; k < i; k++) { d *= 10; }
        *p++ = (char)('0' + (ni / d) % 10);
    }
    *p = '\0';
    return 1;
}

#ifdef __cplusplus
}
#endif
