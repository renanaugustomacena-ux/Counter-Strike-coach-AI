# SECURITY/ — Documentação de Segurança do Macena CS2 Analyzer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Este diretório é a fonte única de verdade para a postura de segurança do `Programma_CS2_RENAN`.
Todos os documentos aqui são versionados, revisados via `CODEOWNERS` e autoritativos.

## Doutrina

Segurança é uma **propriedade estrutural do sistema**, não uma etapa posterior. Modelamos:

```
code → build → artifact → deploy → run
```

com sinais de segurança, loops de feedback e enforcement de policy em cada estágio. Toda decisão não-trivial
neste diretório é defendida com **risk-addressed / residual-risk / tradeoffs / assumptions**.

## Layout

| Arquivo | Propósito |
|---|---|
| [`THREAT_MODEL.md`](THREAT_MODEL.md) | Matriz STRIDE + LINDDUN, DFD, registro de assets, fronteiras de confiança |
| [`CONTROL_CATALOG.md`](CONTROL_CATALOG.md) | Controles mapeados para NIST SSDF, OWASP ASVS L2, CWE Top 25 |
| [`INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md) | Runbooks NIST SP 800-61 r2 para IR-01…IR-05 |
| [`SLSA.md`](SLSA.md) | Postura SLSA Build Level 3 e gap analysis |
| [`CONFIG_REFERENCE.md`](CONFIG_REFERENCE.md) | Variáveis de ambiente: defaults, sensibilidade, validação |
| [`CVE_LOG.md`](CVE_LOG.md) | Log append-only de triagem de CVEs |
| [`BOUNDARY_FILES.txt`](BOUNDARY_FILES.txt) | Lista de arquivos de fronteira de confiança — pull requests que tocam qualquer linha exigem revisão de segurança |
| [`WIPE_RUNBOOK.md`](WIPE_RUNBOOK.md) | Procedimento operacional padrão para `tools/wipe_for_reingest*.py` |
| `policies/` | Regras de policy-as-code consumidas por `tools/policy_runner.py` |
| `waivers.yaml` | Exceções com prazo às policies (cada entrada: `risk:`, `expires:`, `owner:`, `justification:`) |

## Como um colaborador usa este diretório

1. **Antes de escrever código** — leia `THREAT_MODEL.md` para a fronteira de confiança que sua mudança atravessa.
2. **Enquanto escreve** — `tools/policy_runner.py` roda em pre-commit (em warn-mode inicialmente) e previne drift.
3. **Antes do merge** — se sua mudança toca um caminho em `BOUNDARY_FILES.txt`, o CI rotula o pull request com
   `security-review-required` e o `CODEOWNERS` impõe a revisão de segurança.
4. **No release** — `goliath.py audit` executa a cadeia completa (SBOM, atestado SLSA, manifesto de integridade, RASP).
5. **Durante um incidente** — `INCIDENT_RESPONSE.md` define os cenários nomeados; `goliath.py panic` é o kill-switch.

## Ancoragem em padrões

- **NIST SP 800-218 v1.1** (Secure Software Development Framework — SSDF)
- **NIST SP 800-53 r5** / **800-161 r1** (gestão de risco da supply chain)
- **NIST SP 800-61 r2** (computer security incident handling guide)
- **NIST SP 800-63B** (digital identity / authentication)
- **OWASP ASVS 4.0.3 Level 2**
- **OWASP Top 10:2021**
- **CWE Top 25 (2024)**
- **SLSA v1.0** (alvo Build Level 3)
- **CycloneDX 1.6** SBOM
- **ISO/IEC 27001:2022** controles do Annex A A.5–A.8
- **LINDDUN GO (2023)** ameaças de privacidade
- **RFC 6749 / 7636 / 7519 / 7517 / 8252** (OAuth + JWT)
- **OpenID 2.0 Final** (Steam login)
- **OpenID Connect Core 1.0** (FaceIt)
- **GDPR Art. 5** (minimização de dados)

## Contato

Reports de vulnerabilidades ou de preocupações de segurança devem chegar ao dono do repositório:
**Renan Augusto Macena** — veja CODEOWNERS para o roteamento de contato.

Para divulgação coordenada, **não** abra uma issue pública. Use um canal privado.
