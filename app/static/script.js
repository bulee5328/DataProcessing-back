document.addEventListener('DOMContentLoaded', () => {
    const cardGrid = document.querySelector('.card-grid');
    const settingsContainer = document.getElementById('advanced-settings');
    const addedSettings = new Set();

    // 차트 인스턴스 저장 변수
    let allocationChartInstance = null;
    
    // 1. 카드 그리드 이벤트
    cardGrid.addEventListener('click', (e) => {
        if (e.target.classList.contains('indicator-btn')) {
            const indicatorName = e.target.textContent;
            const categoryName = e.target.dataset.category;
            addAdvancedSettingRow(indicatorName, categoryName);
        }
    });

    // 2. 고급 설정 섹션 이벤트
    settingsContainer.addEventListener('click', async (e) => {
        const target = e.target;

        // [수정] "설정값 입력" 버튼만 클릭 확인
        if (target.classList.contains('set-value-btn')) {
            

            // 결과 숨기기
            hideResults();
            
            // 2-1. 가중치 (Metrics) 수집
            const metricsApiPayload = [];
            addedSettings.forEach(name => {
                const safeIdName = name.replace(/ /g, '-').replace(/[\(\)]/g, ''); 
                const inputId = `${safeIdName}-weight`;
                const inputField = document.getElementById(inputId);
                
                if (inputField) {
                    const rawValue = parseFloat(inputField.value);
                    metricsApiPayload.push({
                        name: name,
                        weight: rawValue / 100.0
                    });
                }
            });

            // 2-2. 종목 개수 (Ticker Count) 수집
            const tickerCountInput = document.getElementById('ticker-count-input');
            const tickerCount = tickerCountInput ? parseInt(tickerCountInput.value, 10) : 5;

            const apiUrl = "/api/finance/metrics";
            const payload = {
                "ticker_count": tickerCount,
                "metrics": metricsApiPayload
            };
            
            // 3. API 요청
            try {
                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload) 
                });

                const resultData = await response.json();

                if (response.ok) {
                    // 결과 표시 (차트)
                    displayResultsOnPage(resultData);
                } else {
                    alert(`오류가 발생했습니다: ${resultData.detail || response.statusText}`);
                }
            } catch (error) {
                console.error("Fetch Error:", error);
                alert("API 요청 중 네트워크 오류가 발생했습니다.");
            }
        }
        
        // 삭제 버튼
        if (target.classList.contains('remove-row-btn')) {
            const indicatorName = target.dataset.indicator;
            addedSettings.delete(indicatorName);
            
            const rowToRemove = target.closest('.input-wrapper');
            if (rowToRemove) rowToRemove.remove();

            if (addedSettings.size === 0) {
                const card = settingsContainer.querySelector('.advanced-setting-card');
                if (card) card.remove();
                settingsContainer.classList.remove('active');
            }
        }

        // 값 조절 버튼 (+, -)
        if (target.classList.contains('btn-adjust')) {
            const inputId = target.dataset.indicator;
            const inputField = document.getElementById(inputId);
            
            if (inputField) {
                const isInteger = (target.dataset.step === "1") || (inputField.id === 'ticker-count-input');
                let currentValue = isInteger ? parseInt(inputField.value, 10) : parseFloat(inputField.value);
                const step = isInteger ? 1 : (parseFloat(inputField.step) || 0.1);

                if (target.classList.contains('increment-btn')) { 
                    currentValue += step; 
                } else if (target.classList.contains('decrement-btn')) { 
                    currentValue -= step; 
                }
                
                if (inputField.id === 'ticker-count-input' && currentValue < 1) {
                    currentValue = 1;
                }
                
                inputField.value = isInteger ? currentValue : currentValue.toFixed(1);
            }
        }
    });

    /**
     * 고급 설정 항목 추가
     */
    function addAdvancedSettingRow(name, category) {
        if (addedSettings.has(name)) {
            alert(`${name} 설정은 이미 추가되었습니다.`);
            return;
        }

        // 첫 항목 추가 시 카드 생성
        if (addedSettings.size === 0) {
            settingsContainer.classList.add('active');
            const cardShellHTML = `
                <div class="card advanced-setting-card"> 
                    <div class="card-header"><h3>고급 설정</h3></div>
                    <div class="card-body">
                        <div class="input-wrapper" id="ticker-count-wrapper">
                            <label for="ticker-count-input">종목 개수</label>
                            <div class="input-group">
                                <button class="btn-adjust decrement-btn" data-indicator="ticker-count-input" data-step="1">-</button>
                                <input type="number" id="ticker-count-input" value="5" step="1" min="1" style="text-align: right;"> 
                                <button class="btn-adjust increment-btn" data-indicator="ticker-count-input" data-step="1">+</button>
                            </div>
                            <div style="width: 40px;"></div> 
                        </div>

                        <button class="set-value-btn">설정값 입력</button>
                    </div>
                </div>`;
            settingsContainer.insertAdjacentHTML('beforeend', cardShellHTML);
        }

        const safeIdName = name.replace(/ /g, '-').replace(/[\(\)]/g, '');
        const inputId = `${safeIdName}-weight`;
        
        const rowHTML = `
            <div class="input-wrapper">
                <label for="${inputId}">${category} ${name} 가중치 (%)</label>
                <div class="input-group">
                    <button class="btn-adjust decrement-btn" data-indicator="${inputId}">-</button>
                    <input type="number" id="${inputId}" value="30.0" step="0.1"> 
                    <button class="btn-adjust increment-btn" data-indicator="${inputId}">+</button>
                </div>
                <button class="remove-btn remove-row-btn" data-indicator="${name}">&times;</button>
            </div>`;

        const cardBody = settingsContainer.querySelector('.advanced-setting-card .card-body');
        const tickerCountWrapper = cardBody.querySelector('#ticker-count-wrapper');
        
        if (tickerCountWrapper) {
            tickerCountWrapper.insertAdjacentHTML('beforebegin', rowHTML);
        }
        
        addedSettings.add(name);
    }

    /**
     * 결과 숨김 및 차트 초기화
     */
    function hideResults() {
        document.getElementById('result-display').classList.add('hidden');
        if (allocationChartInstance) {
            allocationChartInstance.destroy();
            allocationChartInstance = null;
        }
    }

    /**
     * 결과 표시 (파이 차트)
     */
    function displayResultsOnPage(apiData) {
        const resultContainer = document.getElementById('result-display');
        const resultBody = document.querySelector('#result-display .result-body');

        // 1. 결과 내용 초기화 및 차트 컨테이너 생성
        resultBody.innerHTML = `
            <h3>종목별 할당 비율</h3>
            <div class="chart-container">
                <canvas id="allocation-chart"></canvas>
            </div>
        `;

        // 2. 유효 데이터 필터링
        const validAllocations = apiData.allocations.filter(a => a.allocation > 0);
        
        if (validAllocations.length === 0) {
             resultBody.querySelector('.chart-container').innerHTML = "<p style='text-align:center; padding:20px;'>표시할 할당 내역이 없습니다.</p>";
        } else {
            const labels = validAllocations.map(a => a.ticker);
            const data = validAllocations.map(a => a.allocation);

            // 3. 차트 그리기
            const ctx = document.getElementById('allocation-chart').getContext('2d');
            allocationChartInstance = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '할당 비율 (%)',
                        data: data,
                        backgroundColor: getChartColors(labels.length),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.label || '';
                                    if (label) label += ': ';
                                    if (context.parsed !== null) {
                                        label += context.parsed.toFixed(2) + '%';
                                    }
                                    return label;
                                }
                            }
                        }
                    }
                }
            });
        }

        // 4. 화면 표시
        resultContainer.classList.remove('hidden');
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function getChartColors(numColors) {
        const colors = [
            '#EB4C7B', '#00B1BE', '#8E44AD', '#F39C12', '#2ECC71',
            '#3498DB', '#E74C3C', '#1ABC9C', '#9B59B6', '#F1C40F'
        ];
        let result = [];
        for (let i = 0; i < numColors; i++) {
            result.push(colors[i % colors.length]);
        }
        return result;
    }
});