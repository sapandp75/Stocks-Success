import { useEffect, useRef, memo } from 'react'

function TradingViewChart({ ticker, height = 600 }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !ticker) return

    containerRef.current.innerHTML = ''

    const wrapper = document.createElement('div')
    wrapper.className = 'tradingview-widget-container__widget'
    wrapper.style.height = '100%'
    wrapper.style.width = '100%'
    containerRef.current.appendChild(wrapper)

    const script = document.createElement('script')
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
    script.type = 'text/javascript'
    script.async = true
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: ticker,
      interval: 'D',
      timezone: 'exchange',
      theme: 'light',
      style: '1',
      locale: 'en',
      range: '12M',
      allow_symbol_change: true,
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: true,
      calendar: false,
      hide_volume: false,
      show_popup_button: true,
      popup_width: '1200',
      popup_height: '800',
      toolbar_bg: '#f0f1f3',
      enable_publishing: false,
      withdateranges: true,
      details: true,
      hotlist: false,
      studies: [
        'MASimple@tv-basicstudies',
        'MASimple@tv-basicstudies',
        'MASimple@tv-basicstudies',
      ],
      studies_overrides: {
        'Moving Average.length': 20,
        'Moving Average.Plot.color': '#2962FF',
        'Moving Average.Plot.linewidth': 2,
        'Moving Average#1.length': 50,
        'Moving Average#1.Plot.color': '#E0B800',
        'Moving Average#1.Plot.linewidth': 2,
        'Moving Average#2.length': 200,
        'Moving Average#2.Plot.color': '#E5484D',
        'Moving Average#2.Plot.linewidth': 2,
      },
      support_host: 'https://www.tradingview.com',
    })

    containerRef.current.appendChild(script)

    return () => {
      if (containerRef.current) containerRef.current.innerHTML = ''
    }
  }, [ticker])

  return (
    <div
      className="tradingview-widget-container"
      ref={containerRef}
      style={{ height: `${height}px`, width: '100%' }}
    />
  )
}

export default memo(TradingViewChart)
