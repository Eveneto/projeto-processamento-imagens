"""Experimento complementar no domínio da frequência. Não entra na contagem."""

import numpy as np


def filtrar_passa_baixa(
    cinza: np.ndarray, fracao_raio: float = 0.12
) -> tuple[np.ndarray, np.ndarray]:
    """Aplica um passa-baixa circular e devolve o espectro em log e a imagem filtrada."""
    if cinza.ndim != 2:
        raise ValueError("A transformada de Fourier deste experimento usa uma imagem em tons de cinza.")
    if not 0 < fracao_raio <= 1:
        raise ValueError("A fração do raio do filtro precisa estar entre 0 e 1.")

    espectro_complexo = np.fft.fftshift(np.fft.fft2(cinza.astype(np.float32)))
    espectro = np.log(np.abs(espectro_complexo) + 1.0).astype(np.float32)
    altura, largura = cinza.shape
    cy, cx = altura // 2, largura // 2
    yy, xx = np.ogrid[:altura, :largura]
    raio = fracao_raio * float(min(altura, largura))
    mascara = ((yy - cy) ** 2 + (xx - cx) ** 2) <= raio ** 2
    filtrado = espectro_complexo * mascara
    reconstruida = np.real(np.fft.ifft2(np.fft.ifftshift(filtrado)))
    reconstruida = np.clip(reconstruida, 0, 255).astype(np.uint8)
    return espectro, reconstruida
