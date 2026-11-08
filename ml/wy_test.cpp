// Test de référence : imprime les buckets du vrai code C++ (vocab_hash.hpp) pour comparer au port Python.
#include <cstdio>
#include <cstring>
#include "swipe_decoder/vocab_hash.hpp"
int main() {
    const char* words[] = {"a", "de", "bruit", "l'heure", "bibliothèque", "poussiéreux", "anticonstitutionnellement",
                           "supercalifragilisticexpialidocious_et_un_mot_tres_tres_long_de_plus_de_quarante_huit_octets",
                           "héhé", "qu'elle", "1234", "neely"};
    for (const char* w : words) {
        uint32_t out[2];
        swipe_decoder::compute_hash_indices_wy(w, strlen(w), 32768, out);
        uint32_t out2[2];
        swipe_decoder::compute_hash_indices_wy(w, strlen(w), 4096, out2);
        printf("%s\t%u\t%u\t%u\t%u\n", w, out[0], out[1], out2[0], out2[1]);
    }
    return 0;
}
