import * as React from 'react'

type ButtonVariant = 'black' | 'ghost'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className = '', variant = 'black', ...props },
  ref
) {
  const variantClass = variant === 'black' ? 'btn-black' : 'btn-ghost'

  return <button ref={ref} className={`btn-core ${variantClass} ui-label ${className}`.trim()} {...props} />
})
