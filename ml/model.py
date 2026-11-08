"""ContextLM français : modèle conforme au contrat de swipe-library (context_lm.cpp).

forward(ids [B,L] int64, hashes [B,L,2] int64) -> h [B,L,E]  (causal)
  - ids : 0 = <OOV>/début, 1..V = mots, NUM_EXACT = mot hors vocabulaire (utilise `hashes`)
Le score d'un mot candidat = h . emb + bias, avec emb/bias exacts (ids < NUM_EXACT) ou la somme des
2 buckets hachés. Seuls opérateurs hors délégué XNNPACK : embedding, clamp, lt, where, sum, unsqueeze,
layer_norm (liste de swipe-library/models/hungry_jellyfish/ops.txt).
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class Block(nn.Module):
    """Convolution causale par canal (mémoire de type DFSMN) + petit MLP, avec résidu."""

    def __init__(self, dim, hidden, kernel, dilation):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.pad = (kernel - 1) * dilation
        self.dw = nn.Conv1d(dim, dim, kernel, dilation=dilation, groups=dim)
        self.up = nn.Conv1d(dim, hidden, 1)
        self.down = nn.Conv1d(hidden, dim, 1)

    def forward(self, x):                      # x: [B, L, E]
        y = self.norm(x).transpose(1, 2)       # [B, E, L]
        y = F.pad(y, (self.pad, 0))
        y = self.dw(y)
        y = self.down(F.relu(self.up(y)))
        return x + y.transpose(1, 2)


class ContextLM(nn.Module):
    def __init__(self, num_exact=32768, buckets=32768, dim=64, hidden=256, layers=4, kernel=4, ctx=16):
        super().__init__()
        self.num_exact, self.buckets, self.dim, self.ctx = num_exact, buckets, dim, ctx
        self.exact_embed = nn.Embedding(num_exact, dim)
        self.exact_bias = nn.Parameter(torch.zeros(num_exact))
        self.hash_embed = nn.Embedding(buckets, dim)
        self.hash_bias = nn.Parameter(torch.zeros(buckets))
        nn.init.normal_(self.exact_embed.weight, std=0.1)
        nn.init.normal_(self.hash_embed.weight, std=0.05)
        self.in_norm = nn.LayerNorm(dim)
        dil = [1, 2, 1, 2, 1, 2, 1, 2]
        self.blocks = nn.ModuleList(Block(dim, hidden, kernel, dil[i % len(dil)]) for i in range(layers))
        self.out_norm = nn.LayerNorm(dim)

    def forward(self, ids, hashes):
        n = self.num_exact
        exact = self.exact_embed(ids.clamp(max=n - 1))
        hashed = self.hash_embed(hashes).sum(dim=2)
        x = torch.where((ids < n).unsqueeze(-1), exact, hashed)
        x = self.in_norm(x)
        for b in self.blocks:
            x = b(x)
        return self.out_norm(x)

    # --- tables de sortie, utilisées par get_embeddings() à l'export ---
    def embeddings(self):
        return (self.exact_embed.weight, self.exact_bias, self.hash_embed.weight, self.hash_bias)


class Exportable(nn.Module):
    """Enveloppe d'export : méthode forward + méthode get_embeddings (deux méthodes dans le .pte)."""

    def __init__(self, lm):
        super().__init__()
        self.lm = lm

    def forward(self, ids, hashes):
        return self.lm(ids, hashes)

    def get_embeddings(self):
        return self.lm.embeddings()
