        function sharePost() {
            if (navigator.share) {
                navigator.share({
                    title: 'T4XNetwork Post #{{ post.postid }}',
                    text: '{{ post.posttext }}',
                    url: window.location.href
                });
            } else {
                navigator.clipboard.writeText(window.location.href).then(() => {
                    showToast('URL copied to clipboard!', 'success');
                });
            }
        }

        function copyText() {
            navigator.clipboard.writeText('{{ post.posttext }}').then(() => {
                showToast('Text copied to clipboard!', 'success');
            });
        }

        function showToast(message, type) {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.classList.add('show');
            }, 100);
            
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    document.body.removeChild(toast);
                }, 300);
            }, 3000);
        }

        document.addEventListener('DOMContentLoaded', function() {
            const dateElement = document.querySelector('.post-date');
            const dateStr = dateElement.textContent;
            const date = new Date(dateStr);
            
            const options = {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            };
            
            dateElement.textContent = date.toLocaleDateString('en-US', options);
        });