import * as React from "react"
import { cn } from "@/lib/cn"

type ButtonVariant = "default" | "outline" | "ghost" | "destructive"
type ButtonSize = "default" | "sm" | "icon"

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

const variantClasses: Record<ButtonVariant, string> = {
  default: "bg-stone-900 text-white hover:bg-stone-800",
  outline: "border border-stone-300 bg-white hover:bg-stone-100 text-stone-900",
  ghost: "hover:bg-stone-100 text-stone-700",
  destructive: "bg-red-600 text-white hover:bg-red-700",
}

const sizeClasses: Record<ButtonSize, string> = {
  default: "h-10 px-4 text-sm",
  sm: "h-8 px-3 text-xs",
  icon: "h-9 w-9",
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stone-400",
        "disabled:pointer-events-none disabled:opacity-50",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  ),
)
Button.displayName = "Button"
