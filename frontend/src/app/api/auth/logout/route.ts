import { NextRequest, NextResponse } from 'next/server';
import { clearAuthCookies, getBackendUrl } from '@/lib/authServer';

export async function POST(request: NextRequest) {
  try {
    const refreshToken = request.cookies.get('refresh_token')?.value;
    const accessToken = request.cookies.get('access_token')?.value;

    if (refreshToken) {
      const backendUrl = getBackendUrl();
      await fetch(`${backendUrl}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {});
    }

    const response = NextResponse.json({
      success: true,
      message: 'Sessão encerrada com sucesso.',
    });

    clearAuthCookies(response);
    return response;
  } catch {
    const response = NextResponse.json({ success: true });
    clearAuthCookies(response);
    return response;
  }
}
