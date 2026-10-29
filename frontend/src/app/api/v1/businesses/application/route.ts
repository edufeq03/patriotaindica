import { NextRequest, NextResponse } from 'next/server';
import { getBackendUrl } from '@/lib/authServer';

// Algoritmos de validação oficial de CPF e CNPJ (Módulo 11)
function isValidCpf(cpf: string): boolean {
  const digits = cpf.replace(/\D/g, '');
  if (digits.length !== 11) return false;
  if (/^(\d)\1{10}$/.test(digits)) return false;

  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(digits[i], 10) * (10 - i);
  }
  let rev = 11 - (sum % 11);
  if (rev === 10 || rev === 11) rev = 0;
  if (rev !== parseInt(digits[9], 10)) return false;

  sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(digits[i], 10) * (11 - i);
  }
  rev = 11 - (sum % 11);
  if (rev === 10 || rev === 11) rev = 0;
  if (rev !== parseInt(digits[10], 10)) return false;

  return true;
}

function isValidCnpj(cnpj: string): boolean {
  const digits = cnpj.replace(/\D/g, '');
  if (digits.length !== 14) return false;
  if (/^(\d)\1{13}$/.test(digits)) return false;

  const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(digits[i], 10) * weights1[i];
  }
  let rev = sum % 11 < 2 ? 0 : 11 - (sum % 11);
  if (rev !== parseInt(digits[12], 10)) return false;

  const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  sum = 0;
  for (let i = 0; i < 13; i++) {
    sum += parseInt(digits[i], 10) * weights2[i];
  }
  rev = sum % 11 < 2 ? 0 : 11 - (sum % 11);
  if (rev !== parseInt(digits[13], 10)) return false;

  return true;
}

export async function POST(request: NextRequest) {
  let body: any;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { detail: 'Payload JSON inválido.' },
      { status: 400 }
    );
  }

  // 1. Tenta encaminhar para o backend FastAPI
  try {
    const backendUrl = getBackendUrl();
    const clientIp =
      request.headers.get('cf-connecting-ip') ||
      request.headers.get('x-forwarded-for') ||
      '127.0.0.1';

    const res = await fetch(`${backendUrl}/businesses/application`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': clientIp,
      },
      body: JSON.stringify(body),
    });

    const data = await res.json().catch(() => null);

    if (data) {
      return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(
      { detail: 'Resposta vazia ou inválida do servidor backend.' },
      { status: res.status || 500 }
    );
  } catch (err: unknown) {
    const errorMsg =
      err instanceof Error
        ? err.message
        : 'Não foi possível conectar ao backend. Verifique se o serviço está ativo.';
    return NextResponse.json({ detail: errorMsg }, { status: 502 });
  }
}
