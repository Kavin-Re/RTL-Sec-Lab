# Lab 3 answer key

1. HW(255 - x) = 8 - HW(x), so the model of the complement guess is an exact affine flip of the true model and correlates with -r. The sign is information: the true leak is positive, so taking the maximum of the signed value removes the ambiguity; ranking by |r| would tie the two (the explorer shows both bars).
2. Byte b of the sum depends on the carry out of bytes 0..b-1, which depends on k0's lower bytes. With a wrong low byte, the computed carry into byte b is wrong on every trace where the true and the guessed low part overflow differently, so the hypothesis for byte b is partly wrong even for the right guess and its correlation drops. Byte 0 has no carry in, so it is attacked first, and its result feeds byte 1, and so on.
3. The correlation of the right guess is about sqrt(var_signal / (var_signal + sigma^2)) and the statistic needs r*sqrt(N) above a fixed threshold (wrong guesses sit near 1/sqrt(N)), so for small r the required N is about proportional to sigma^2/var_signal: x4 for 2x sigma (measured 4.0). Added noise therefore only buys a polynomial factor; it is not a substitute for masking, and the attacker can average if the noise is uncorrelated and the alignment is perfect.

Stretch (T7): with HD leakage HW(old ^ s) bit 7 of the old value cancels in old ^ (old + v3), so g and g ^ 0x80 give identical hypotheses; the final byte needs another discriminator.

Common mistakes: forgetting to XOR the constant C3 / C2 into the hypothesis; correlating stage 2 before recovering k1; recomputing the carry with all of k0 instead of the lower bytes only; using `argmax(abs(r))`.
