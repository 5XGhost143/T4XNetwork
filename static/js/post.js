        const likeBtn = document.getElementById('likeBtn');
        const likeCount = document.getElementById('likeCount');
        const toast = document.getElementById('toast');

        updateLikeButton();

        function updateLikeButton() {
            if (isLiked) {
                likeBtn.classList.add('liked');
            } else {
                likeBtn.classList.remove('liked');
            }
            likeCount.textContent = currentLikeCount;
        }

        async function toggleLike() {
            likeBtn.disabled = true;

            try {
                const response = await fetch('/toggle_like', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        postid: postId
                    })
                });

                const data = await response.json();

                if (data.success) {
                    isLiked = data.liked;
                    currentLikeCount = data.like_count;
                    updateLikeButton();
                    showToast(data.message);
                } else {
                    showToast('Error: ' + data.message);
                }
            } catch (error) {
                console.error('Error toggling like:', error);
                showToast('Error occurred while toggling like');
            } finally {
                likeBtn.disabled = false;
            }
        }

        function showToast(message) {
            toast.textContent = message;
            toast.classList.add('show');
            
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        async function refreshLikeStatus() {
            try {
                const response = await fetch(`/get_like_status/${postId}`);
                const data = await response.json();
                
                if (data.success) {
                    isLiked = data.liked;
                    currentLikeCount = data.like_count;
                    updateLikeButton();
                }
            } catch (error) {
                console.error('Error refreshing like status:', error);
            }
        }

        refreshLikeStatus();