import Image from 'next/image';

interface BrasilLogoProps {
  className?: string;
  size?: number;
}

export function BrasilLogo({ className = 'w-9 h-9', size = 36 }: BrasilLogoProps) {
  return (
    <Image
      src="/icon.svg"
      alt="Bandeira Patriota Indica"
      width={size}
      height={size}
      unoptimized
      priority
      className={`rounded-xl shadow-md border border-amber-500/30 shrink-0 ${className}`}
    />
  );
}
