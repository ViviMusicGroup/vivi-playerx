document.addEventListener('DOMContentLoaded', () => {
    let allPlayers = {};

    // Elements
    const mappingsCountEl = document.getElementById('mappings-count');
    const searchInput = document.getElementById('search-input');
    const cardsContainer = document.getElementById('cards-container');
    const loadingState = document.getElementById('loading-state');
    const noResultsState = document.getElementById('no-results-state');

    // Fetch player configurations
    fetch('player_configs.json')
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        })
        .then(data => {
            allPlayers = data.players || {};
            
            // Hide loading indicator
            loadingState.classList.add('hidden');

            // Render stats
            const hashes = Object.keys(allPlayers);
            mappingsCountEl.innerText = hashes.length;

            // Render player list items
            renderPlayerList(allPlayers);
        })
        .catch(err => {
            console.error("Failed to load configs:", err);
            loadingState.innerText = "Failed to load decryption mappings. Is the node offline?";
            loadingState.classList.remove('hidden');
            mappingsCountEl.innerText = "Error";
        });

    // Search filter logic
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        
        if (!query) {
            renderPlayerList(allPlayers);
            noResultsState.classList.add('hidden');
            return;
        }

        const filtered = {};
        for (const [hash, data] of Object.entries(allPlayers)) {
            const signature = (data.sig || "").toLowerCase();
            const nClass = (data.nClass || "").toLowerCase();
            const aliases = (data.aliases || []).join(' ').toLowerCase();

            if (hash.includes(query) || signature.includes(query) || nClass.includes(query) || aliases.includes(query)) {
                filtered[hash] = data;
            }
        }

        if (Object.keys(filtered).length === 0) {
            cardsContainer.innerHTML = '';
            noResultsState.classList.remove('hidden');
        } else {
            noResultsState.classList.add('hidden');
            renderPlayerList(filtered);
        }
    });

    // Render list function
    function renderPlayerList(playersMap) {
        cardsContainer.innerHTML = '';

        for (const [hash, data] of Object.entries(playersMap)) {
            const item = document.createElement('div');
            item.className = 'py-5 px-4 flex flex-col md:flex-row md:items-center justify-between gap-6 hover:bg-white/[0.015] rounded-xl transition-all duration-150';

            // Base fields
            const sig = data.sig || "N/A";
            const nClass = data.nClass || "N/A";
            const sts = data.sts || "N/A";
            const aliasesList = data.aliases || [];

            // Alias badge formatting
            let aliasesHtml = '';
            if (aliasesList.length > 0) {
                aliasesHtml = `
                    <div class="flex items-center gap-1.5 mt-1.5">
                        <span class="text-[10px] text-vivi-blue/60 uppercase font-semibold">Aliases:</span>
                        <div class="flex flex-wrap gap-1">
                            ${aliasesList.map(a => `<span class="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-white/70">${a}</span>`).join('')}
                        </div>
                    </div>
                `;
            }

            item.innerHTML = `
                <!-- Left: Hash details -->
                <div class="flex-grow max-w-sm">
                    <div class="flex items-center gap-3">
                        <span class="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
                        <span class="text-base font-bold font-geist text-white select-all">${hash}</span>
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-vivi-blue/10 border border-vivi-blue/20 text-vivi-blue font-medium">sts:${sts}</span>
                    </div>
                    ${aliasesHtml}
                </div>

                <!-- Right: Monospace fields -->
                <div class="flex flex-col sm:flex-row gap-4 md:gap-8 flex-shrink-0 w-full md:w-auto">
                    <div class="w-full sm:w-64">
                        <span class="text-[10px] font-semibold text-vivi-blue/60 tracking-wider uppercase block mb-1 font-geist">Signature Cipher</span>
                        <code class="code-block block p-2 rounded-lg text-xs break-all text-white border border-white/5 select-all">${sig}</code>
                    </div>
                    <div class="w-full sm:w-48">
                        <span class="text-[10px] font-semibold text-vivi-blue/60 tracking-wider uppercase block mb-1 font-geist">N-Throttle Class</span>
                        <code class="code-block block p-2 rounded-lg text-xs break-all text-emerald-400 border border-white/5 select-all">${nClass}</code>
                    </div>
                </div>
            `;

            cardsContainer.appendChild(item);
        }
    }
});
