import { NextRequest, NextResponse } from 'next/server';
import { setAuthCookies } from '@/lib/authServer';

export async function POST(request: NextRequest) {
  try {
    const { access_token, refresh_token } = await request.json();

    if (!access_token) {
      return NextResponse.json({ detail: 'Token ausente.' }, { status: 400 });
    }

    const response = NextResponse.json({ success: true });
    setAuthCookies(response, access_token, refresh_token);
    return response;
  } catch {
    return NextResponse.json({ detail: 'Erro ao registrar sessão.' }, { status: 500 });
  }
}
