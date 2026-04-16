import * as React from "react"
import { cn } from "@/lib/cn"

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "h-10 w-full rounded-md border border-stone-300 bg-white px-3 text-sm",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stone-400",
      "disabled:opacity-50",
      className,
    )}
    {...props}
  >
    {children}
  </select>
))
Select.displayName = "Select"
