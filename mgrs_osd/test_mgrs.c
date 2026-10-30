/* Reads "lat lon" pairs (degrees) from stdin, prints MGRS at 5 digits. */
#include <stdio.h>
#include "mgrs_core.h"

int main(void)
{
    double lat, lon;
    char buf[32];
    while (scanf("%lf %lf", &lat, &lon) == 2) {
        if (mgrs_format((int32_t)llround(lat * 1e7), (int32_t)llround(lon * 1e7), 5, buf, sizeof(buf))) {
            printf("%s\n", buf);
        } else {
            printf("NONE\n");
        }
    }
    return 0;
}
